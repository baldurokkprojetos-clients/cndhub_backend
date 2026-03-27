from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.models.base import Cliente, Usuario, Hub, Certidao, Job, TipoCertidao
from app.schemas.schemas import ClienteCreate, ClienteUpdate, ClienteResponse
from app.api.deps import get_current_user, CurrentUser
from app.core.security import create_verification_token, get_password_hash
from app.core.email import send_verification_email_async
import uuid
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[ClienteResponse])
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = db.query(Cliente)
    
    if current_user.role == "admin":
        if current_user.hub_ids:
            query = query.filter(Cliente.hub_id.in_(current_user.hub_ids))
        else:
            return []
    elif current_user.role == "cliente":
        if current_user.cliente_ids:
            query = query.filter(Cliente.id.in_(current_user.cliente_ids))
        else:
            return []
        
    clientes = query.all()
    cliente_ids = [cliente.id for cliente in clientes]
    tipos_por_cliente = {}
    if cliente_ids:
        certidoes = db.query(Certidao.cliente_id, Certidao.tipo_certidao_id).filter(
            Certidao.cliente_id.in_(cliente_ids)
        ).all()
        for cliente_id, tipo_id in certidoes:
            tipos_por_cliente.setdefault(cliente_id, []).append(str(tipo_id))
    
    for cliente in clientes:
        setattr(cliente, "tipos_certidoes", tipos_por_cliente.get(cliente.id, []))
        
    return clientes

@router.post("/", response_model=ClienteResponse)
def criar_cliente(
    cliente: ClienteCreate, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role == "cliente":
        raise HTTPException(status_code=403, detail="Clientes não podem criar novos clientes.")
        
    cliente_data = cliente.model_dump(exclude={"tipos_certidoes"})
    
    if current_user.role == "admin" and current_user.hub_ids:
        if len(current_user.hub_ids) == 1:
            cliente_data["hub_id"] = current_user.hub_ids[0]
        elif not cliente_data.get("hub_id") or cliente_data["hub_id"] not in current_user.hub_ids:
            raise HTTPException(status_code=400, detail="Admin deve selecionar uma HUB válida para o cliente.")
        
    # Criar cliente
    db_cliente = Cliente(**cliente_data)
    db.add(db_cliente)
    db.flush()
    
    # Adicionar certidões e jobs se o cliente estiver ativo
    if cliente.ativo and cliente.tipos_certidoes:
        for tipo_id in cliente.tipos_certidoes:
            # Verifica se o tipo de certidão existe
            tipo = db.query(TipoCertidao).filter(TipoCertidao.id == tipo_id).first()
            if not tipo:
                continue
                
            # Cria a certidão associada
            nova_certidao = Certidao(
                cliente_id=db_cliente.id,
                tipo_certidao_id=tipo_id,
                status="pending"
            )
            db.add(nova_certidao)
            db.flush()
            
            # Cria o job para processar a certidão
            novo_job = Job(
                tipo="emitir_certidao",
                cliente_id=db_cliente.id,
                certidao_id=nova_certidao.id,
                status="pending"
            )
            db.add(novo_job)
    
    # Criar usuário automático se houver email
    if cliente.email:
        existing_user = db.query(Usuario).filter(Usuario.email == cliente.email).first()
        if not existing_user:
            hub_id = cliente_data.get("hub_id")
            if not hub_id:
                hub = db.query(Hub).first()
                if not hub:
                    hub = Hub(nome="Hub Principal", api_key=str(uuid.uuid4()))
                    db.add(hub)
                    db.commit()
                    db.refresh(hub)
                hub_id = hub.id

            db_user = Usuario(
                nome=cliente.responsavel or cliente.razao_social,
                email=cliente.email,
                telefone=cliente.telefone,
                role="cliente",
                ativo=True,
                hub_id=hub_id,
                senha_hash=get_password_hash("Mudar123!") # Senha padrão
            )
            
            # Recuperar a Hub correta para o relacionamento
            hub_obj = db.query(Hub).filter(Hub.id == hub_id).first()
            if hub_obj:
                db_user.hubs = [hub_obj]
                
            db_user.clientes = [db_cliente]
            db.add(db_user)
            
            # Gerar token e enviar email de validação
            token = create_verification_token(db_user.email)
            asyncio.create_task(send_verification_email_async(db_user.email, token))

    db.commit()
    db.refresh(db_cliente)
    
    # Preencher tipos_certidoes
    certidoes = db.query(Certidao.tipo_certidao_id).filter(Certidao.cliente_id == db_cliente.id).all()
    setattr(db_cliente, "tipos_certidoes", [str(c[0]) for c in certidoes])
    
    return db_cliente

@router.put("/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(
    cliente_id: UUID, 
    cliente: ClienteUpdate, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role == "cliente":
        raise HTTPException(status_code=403, detail="Clientes não podem editar dados.")
        
    db_cliente = db.query(Cliente).filter(Cliente.id == str(cliente_id)).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    if current_user.role == "admin" and db_cliente.hub_id not in current_user.hub_ids:
        raise HTTPException(status_code=403, detail="Acesso negado a este cliente.")
    
    logger.info(f"Atualizando cliente {cliente_id}")
    update_data = cliente.model_dump(exclude_unset=True, exclude={"tipos_certidoes"})
    if current_user.role == "admin" and update_data.get("hub_id") and update_data["hub_id"] not in current_user.hub_ids:
        raise HTTPException(status_code=403, detail="Acesso negado para alterar HUB deste cliente.")
    for key, value in update_data.items():
        setattr(db_cliente, key, value)
        
    db.flush()

    # Atualizar tipos de certidões e jobs
    if "tipos_certidoes" in cliente.model_dump(exclude_unset=True) and db_cliente.ativo:
        logger.info(f"Atualizando certidões do cliente {cliente_id}")
        # Obter certidões atuais do cliente
        certidoes_atuais = db.query(Certidao).filter(Certidao.cliente_id == db_cliente.id).all()
        tipos_atuais_ids = {str(c.tipo_certidao_id) for c in certidoes_atuais}
        
        novos_tipos = set(cliente.tipos_certidoes) if cliente.tipos_certidoes else set()
        
        # Adicionar novos
        tipos_para_adicionar = novos_tipos - tipos_atuais_ids
        for tipo_id in tipos_para_adicionar:
            tipo = db.query(TipoCertidao).filter(TipoCertidao.id == tipo_id).first()
            if not tipo:
                continue
            nova_certidao = Certidao(
                cliente_id=db_cliente.id,
                tipo_certidao_id=tipo_id,
                status="pending"
            )
            db.add(nova_certidao)
            db.flush()
            novo_job = Job(
                tipo="emitir_certidao",
                cliente_id=db_cliente.id,
                certidao_id=nova_certidao.id,
                status="pending"
            )
            db.add(novo_job)
            
        # Remover (inativar/deletar) os que foram desmarcados
        tipos_para_remover = tipos_atuais_ids - novos_tipos
        if tipos_para_remover:
            certidoes_remover = db.query(Certidao).filter(
                Certidao.cliente_id == db_cliente.id,
                Certidao.tipo_certidao_id.in_(tipos_para_remover)
            ).all()
            
            certidoes_remover_ids = [c.id for c in certidoes_remover]
            if certidoes_remover_ids:
                # Deletar jobs associados
                db.query(Job).filter(Job.certidao_id.in_(certidoes_remover_ids)).delete(synchronize_session=False)
                # Deletar certidoes
                db.query(Certidao).filter(Certidao.id.in_(certidoes_remover_ids)).delete(synchronize_session=False)
        
    db.commit()
    db.refresh(db_cliente)
    
    # Preencher tipos_certidoes
    certidoes = db.query(Certidao.tipo_certidao_id).filter(Certidao.cliente_id == db_cliente.id).all()
    setattr(db_cliente, "tipos_certidoes", [str(c[0]) for c in certidoes])
    
    return db_cliente

@router.delete("/{cliente_id}")
def excluir_cliente(
    cliente_id: UUID, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    if current_user.role == "cliente":
        raise HTTPException(status_code=403, detail="Clientes não podem excluir dados.")
        
    db_cliente = db.query(Cliente).filter(Cliente.id == str(cliente_id)).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    if current_user.role == "admin" and db_cliente.hub_id not in current_user.hub_ids:
        raise HTTPException(status_code=403, detail="Acesso negado a este cliente.")
    
    db.delete(db_cliente)
    db.commit()
    return {"message": "Cliente excluído com sucesso"}
