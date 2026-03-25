from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.base import Usuario, Hub, Cliente
from app.schemas.schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from app.api.deps import get_current_user, CurrentUser
from app.core.security import create_verification_token, get_password_hash
from app.core.email import send_verification_email
from typing import List
import uuid

router = APIRouter()

@router.post("/", response_model=UsuarioResponse)
def create_usuario(usuario: UsuarioCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    db_usuario = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Validar regras de criação por perfil
    if current_user.role == "admin":
        if usuario.role == "master":
            raise HTTPException(status_code=403, detail="Admin não pode criar usuário master")
        # Se admin criar admin, tem que ser na mesma hub
        if usuario.role == "admin" and not usuario.hub_ids:
            usuario.hub_ids = current_user.hub_ids
        if usuario.hub_ids:
            for hid in usuario.hub_ids:
                if hid not in current_user.hub_ids:
                    raise HTTPException(status_code=403, detail="Admin só pode vincular a hubs que já possui acesso")
                    
    if current_user.role == "cliente":
        if usuario.role in ["master", "admin"]:
            raise HTTPException(status_code=403, detail="Cliente só pode criar usuário cliente")
        if usuario.cliente_ids:
            for cid in usuario.cliente_ids:
                if cid not in current_user.cliente_ids:
                    raise HTTPException(status_code=403, detail="Cliente só pode vincular a clientes que já possui acesso")
        else:
            usuario.cliente_ids = current_user.cliente_ids
    
    # Se nao enviou hub_id, pega o primeiro hub ou cria um (Apenas para fallback antigo, o ideal é usar hub_ids)
    hub_id = usuario.hub_id
    if not hub_id and not usuario.hub_ids:
        hub = db.query(Hub).first()
        if not hub:
            hub = Hub(nome="Hub Principal", api_key=str(uuid.uuid4()))
            db.add(hub)
            db.commit()
            db.refresh(hub)
        hub_id = hub.id

    db_user = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        telefone=usuario.telefone,
        role=usuario.role,
        ativo=usuario.ativo,
        hub_id=hub_id,
        cliente_id=usuario.cliente_id,
        senha_hash=get_password_hash(usuario.senha)
    )
    
    # Vincula os hubs enviados, se existirem
    if usuario.hub_ids:
        hubs = db.query(Hub).filter(Hub.id.in_(usuario.hub_ids)).all()
        db_user.hubs = hubs
    elif hub_id:
        hub = db.query(Hub).filter(Hub.id == hub_id).first()
        if hub:
            db_user.hubs = [hub]

    # Vincula os clientes enviados, se existirem
    if usuario.cliente_ids:
        clientes = db.query(Cliente).filter(Cliente.id.in_(usuario.cliente_ids)).all()
        db_user.clientes = clientes
        if usuario.role == "cliente":
            hub_ids_from_clientes = {c.hub_id for c in clientes if c.hub_id}
            if hub_ids_from_clientes:
                db_user.hubs = db.query(Hub).filter(Hub.id.in_(list(hub_ids_from_clientes))).all()
    elif usuario.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == usuario.cliente_id).first()
        if cliente:
            db_user.clientes = [cliente]
            if usuario.role == "cliente" and cliente.hub_id:
                db_user.hubs = [db.query(Hub).filter(Hub.id == cliente.hub_id).first()]

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Gerar token e enviar email de validação
    token = create_verification_token(db_user.email)
    background_tasks.add_task(send_verification_email, db_user.email, token)
    
    return db_user

@router.get("/", response_model=List[UsuarioResponse])
def read_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    try:
        query = db.query(Usuario)
        
        if current_user.role == "admin":
            # Admin vê usuários das suas hubs, exceto master
            query = query.filter(
                Usuario.hubs.any(Hub.id.in_(current_user.hub_ids)),
                Usuario.role != "master"
            )
        elif current_user.role == "cliente":
            # Cliente vê usuários dos seus clientes, apenas cliente
            query = query.filter(
                Usuario.clientes.any(Cliente.id.in_(current_user.cliente_ids)),
                Usuario.role == "cliente"
            )
            
        usuarios = query.offset(skip).limit(limit).all()
        return usuarios
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{usuario_id}", response_model=UsuarioResponse)
def read_usuario(usuario_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario not found")
        
    if current_user.role == "admin":
        # Check if user has any hub in common
        user_hub_ids = [h.id for h in usuario.hubs]
        if not any(hid in current_user.hub_ids for hid in user_hub_ids):
            raise HTTPException(status_code=403, detail="Acesso negado")
    elif current_user.role == "cliente":
        user_cliente_ids = [c.id for c in usuario.clientes]
        if not any(cid in current_user.cliente_ids for cid in user_cliente_ids):
            raise HTTPException(status_code=403, detail="Acesso negado")
            
    return usuario

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def update_usuario(usuario_id: str, usuario_update: UsuarioUpdate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario not found")
        
    if current_user.role == "admin":
        # Check if user has any hub in common
        user_hub_ids = [h.id for h in db_usuario.hubs]
        if not any(hid in current_user.hub_ids for hid in user_hub_ids):
            raise HTTPException(status_code=403, detail="Acesso negado")
            
        if usuario_update.role == "master":
             raise HTTPException(status_code=403, detail="Admin não pode mudar perfil para master")
             
    elif current_user.role == "cliente":
        user_cliente_ids = [c.id for c in db_usuario.clientes]
        if not any(cid in current_user.cliente_ids for cid in user_cliente_ids):
            raise HTTPException(status_code=403, detail="Acesso negado")
            
        if usuario_update.role in ["master", "admin"]:
            raise HTTPException(status_code=403, detail="Cliente só pode ter perfil cliente")
    
    update_data = usuario_update.model_dump(exclude_unset=True)
    if "senha" in update_data:
        update_data["senha_hash"] = get_password_hash(update_data.pop("senha"))
        
    hub_ids = update_data.pop("hub_ids", None)
    cliente_ids = update_data.pop("cliente_ids", None)
        
    for key, value in update_data.items():
        setattr(db_usuario, key, value)
        
    if hub_ids is not None:
        hubs = db.query(Hub).filter(Hub.id.in_(hub_ids)).all()
        db_usuario.hubs = hubs
        
    if cliente_ids is not None:
        clientes = db.query(Cliente).filter(Cliente.id.in_(cliente_ids)).all()
        db_usuario.clientes = clientes
        
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.delete("/{usuario_id}")
def delete_usuario(usuario_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    db_usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if db_usuario is None:
        raise HTTPException(status_code=404, detail="Usuario not found")
        
    if current_user.role == "admin":
        user_hub_ids = [h.id for h in db_usuario.hubs]
        if not any(hid in current_user.hub_ids for hid in user_hub_ids):
            raise HTTPException(status_code=403, detail="Acesso negado")
    elif current_user.role == "cliente":
        user_cliente_ids = [c.id for c in db_usuario.clientes]
        if not any(cid in current_user.cliente_ids for cid in user_cliente_ids):
            raise HTTPException(status_code=403, detail="Acesso negado")
            
    db.delete(db_usuario)
    db.commit()
    return {"message": "Usuario deleted successfully"}
