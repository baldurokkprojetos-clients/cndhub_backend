from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Any
from uuid import UUID
import shutil
import os
from pathlib import Path
from app.core.database import get_db
from app.models.base import Certidao, Cliente
from app.schemas.schemas import CertidaoResponse
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.core.config import settings
from supabase import create_client, Client
import logging
from app.api.deps import get_current_user, CurrentUser, verify_worker_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

# Inicializar cliente do Supabase
supabase: Optional[Client] = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Erro ao inicializar Supabase client: {e}")

@router.get("/", response_model=List[CertidaoResponse])
def listar_certidoes(
    cliente_id: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    query = db.query(Certidao)
    
    if current_user.role == "admin":
        if current_user.hub_ids:
            query = query.join(Cliente).filter(Cliente.hub_id.in_(current_user.hub_ids))
        else:
            return []
    elif current_user.role == "cliente":
        if current_user.cliente_ids:
            # Limita aos clientes do usuário logado
            query = query.filter(Certidao.cliente_id.in_(current_user.cliente_ids))
        else:
            return []
        
    if cliente_id:
        query = query.filter(Certidao.cliente_id == cliente_id)
        
    return query.all()

@router.get("/{certidao_id}/download")
def download_certidao(
    certidao_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    certidao = db.query(Certidao).filter(Certidao.id == certidao_id).first()
    if not certidao:
        raise HTTPException(status_code=404, detail="Certidão não encontrada")
        
    # Validar permissão
    if current_user.role == "cliente":
        if str(certidao.cliente_id) not in current_user.cliente_ids:
            raise HTTPException(status_code=403, detail="Acesso negado")
    elif current_user.role == "admin":
        cliente = db.query(Cliente).filter(Cliente.id == certidao.cliente_id).first()
        if not cliente or str(cliente.hub_id) not in current_user.hub_ids:
            raise HTTPException(status_code=403, detail="Acesso negado")
            
    if certidao.arquivo_conteudo:
        filename = "certidao.pdf"
        if certidao.caminho_arquivo:
            filename = certidao.caminho_arquivo.split("/")[-1]
            
        return Response(
            content=certidao.arquivo_conteudo,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    # Se não tiver o conteúdo binário, tenta pelo caminho local ou URL
    if certidao.caminho_arquivo:
        # Se for uma URL pública
        if certidao.caminho_arquivo.startswith("http"):
            return {"url": certidao.caminho_arquivo}
            
        # Se for um arquivo local
        import os
        from fastapi.responses import FileResponse
        
        # Tenta o caminho exato primeiro (caso seja um caminho absoluto do worker na mesma máquina)
        if os.path.exists(certidao.caminho_arquivo):
            filename = os.path.basename(certidao.caminho_arquivo)
            return FileResponse(path=certidao.caminho_arquivo, filename=filename, media_type="application/pdf")
            
        # Pega apenas o nome do arquivo, lidando com barras e contrabarras
        filename = certidao.caminho_arquivo.replace("\\", "/").split("/")[-1]
        local_path = f"storage/certidoes/{filename}"
        if os.path.exists(local_path):
            return FileResponse(path=local_path, filename=filename, media_type="application/pdf")
            
    raise HTTPException(status_code=404, detail="Arquivo da certidão não encontrado no banco de dados nem no disco")

@router.post("/upsert", response_model=CertidaoResponse)
def upsert_certidao(
    cliente_id: str = Form(...),
    tipo_certidao_id: str = Form(...),
    status: str = Form(...),
    mensagem_erro: Optional[str] = Form(None),
    caminho_arquivo: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    hub: Any = Depends(verify_worker_api_key)
) -> Any:
    # Verify if cliente exists
    from app.models.base import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.hub_id == hub.id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente com ID {cliente_id} não encontrado ou não pertence a esta HUB.")

    path_to_save = caminho_arquivo
    
    arquivo_conteudo_bytes = None
    
    # Se um arquivo foi enviado, salvamos na pasta local de armazenamento do backend e no banco de dados
    if file:
        arquivo_conteudo_bytes = file.file.read()
        file.file.seek(0) # Reset pointer just in case we need to read it again

        base_dir = Path("storage/certidoes")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Padrão: usar o nome enviado pelo worker (ex: CNPJ_TIPO_DATA.pdf)
        file_name = file.filename
        if not file_name:
            ext = ".pdf"
            file_name = f"{tipo_certidao_id}_{cliente_id}{ext}"
            
        file_path = base_dir / file_name
        
        # Deletar arquivos antigos do mesmo tipo para este cliente no storage do backend
        # Para evitar encher o disco com arquivos velhos
        for old_file in base_dir.glob(f"*{tipo_certidao_id}*"):
            try:
                if old_file.is_file() and old_file.name != file_name:
                    old_file.unlink()
            except Exception:
                pass
            
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Salva o caminho relativo que será servido pelo backend (fallback)
        path_to_save = f"/storage/certidoes/{file_name}"

        # Upload para o Supabase Storage, se configurado
        if supabase:
            try:
                # O caminho no storage pode ser: cliente_id/file_name
                storage_path = f"{cliente_id}/{file_name}"
                
                # Deleta o arquivo anterior se existir com o mesmo nome para evitar conflito (opcional)
                try:
                    supabase.storage.from_(settings.SUPABASE_BUCKET).remove([storage_path])
                except Exception:
                    pass
                
                with open(file_path, "rb") as f:
                    supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
                        path=storage_path,
                        file=f,
                        file_options={"content-type": "application/pdf"}
                    )
                
                # Gera URL pública
                public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(storage_path)
                path_to_save = public_url
            except Exception as e:
                logger.error(f"Erro ao fazer upload para o Supabase: {e}")
                # Fallback para o caminho local mantido

    # Verifica se já existe para fazer o update manual
    existente = db.query(Certidao).filter(
        Certidao.cliente_id == cliente_id,
        Certidao.tipo_certidao_id == tipo_certidao_id
    ).first()

    if existente:
        existente.status = status
        existente.caminho_arquivo = path_to_save if path_to_save else existente.caminho_arquivo
        if arquivo_conteudo_bytes is not None:
            existente.arquivo_conteudo = arquivo_conteudo_bytes
        existente.mensagem_erro = mensagem_erro
        existente.atualizado_em = func.now()
        upserted_certidao = existente
    else:
        nova_certidao = Certidao(
            cliente_id=cliente_id,
            tipo_certidao_id=tipo_certidao_id,
            status=status,
            caminho_arquivo=path_to_save,
            arquivo_conteudo=arquivo_conteudo_bytes,
            mensagem_erro=mensagem_erro
        )
        db.add(nova_certidao)
        upserted_certidao = nova_certidao
        
    db.commit()
    db.refresh(upserted_certidao)
    
    return upserted_certidao

