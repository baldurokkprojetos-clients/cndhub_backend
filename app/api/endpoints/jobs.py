from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.database import get_db
from app.models.base import Job, Cliente, TipoCertidao, Certidao
from datetime import datetime, timezone, timedelta
import os

from pydantic import BaseModel

from app.api.deps import get_current_user, CurrentUser, verify_worker_api_key

router = APIRouter()

class JobCreate(BaseModel):
    cliente_id: str
    tipo_certidao_id: str
    tipo: str = "emitir_certidao"

@router.post("/", status_code=201)
def create_job(
    job_in: JobCreate, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Cria um novo job na fila para ser processado pelo Worker."""
    cliente = db.query(Cliente).filter(Cliente.id == job_in.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    if current_user.role == "admin" and cliente.hub_id not in current_user.hub_ids:
        raise HTTPException(status_code=403, detail="Acesso negado a este cliente.")
    if current_user.role == "cliente" and cliente.id not in current_user.cliente_ids:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas clientes vinculados permitidos.")
        
    tipo_cert = db.query(TipoCertidao).filter(TipoCertidao.id == job_in.tipo_certidao_id).first()
    if not tipo_cert:
        raise HTTPException(status_code=404, detail="Tipo de Certidão não encontrado")

    new_certidao = db.query(Certidao).filter(
        Certidao.cliente_id == job_in.cliente_id,
        Certidao.tipo_certidao_id == job_in.tipo_certidao_id
    ).first()
    
    if not new_certidao:
        new_certidao = Certidao(
            cliente_id=job_in.cliente_id,
            tipo_certidao_id=job_in.tipo_certidao_id,
            status="pending"
        )
        db.add(new_certidao)
        db.commit()
        db.refresh(new_certidao)
    else:
        new_certidao.status = "pending"
        db.commit()

    # Verifica se já existe um job pendente para evitar duplicidade
    existing_job = db.query(Job).filter(
        Job.cliente_id == job_in.cliente_id,
        Job.certidao_id == new_certidao.id,
        Job.status == "pending"
    ).first()
    
    if existing_job:
        raise HTTPException(status_code=400, detail="Já existe um job pendente para esta certidão e cliente")

    new_job = Job(
        tipo=job_in.tipo,
        cliente_id=job_in.cliente_id,
        certidao_id=new_certidao.id,
        status="pending"
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return {"message": "Job criado com sucesso", "job_id": new_job.id}

@router.get("/")
def listar_jobs(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Lista todos os jobs (Apenas Master)."""
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito a Master")
        
    jobs = (
        db.query(
            Job,
            Cliente.razao_social.label("cliente_nome"),
            Certidao.status.label("certidao_status"),
            TipoCertidao.nome.label("tipo_cert_nome")
        )
        .join(Cliente, Cliente.id == Job.cliente_id)
        .outerjoin(Certidao, Certidao.id == Job.certidao_id)
        .outerjoin(TipoCertidao, TipoCertidao.id == Certidao.tipo_certidao_id)
        .order_by(Job.created_at.desc())
        .all()
    )
    result = []
    for job, cliente_nome, certidao_status, tipo_cert_nome in jobs:
        result.append({
            "id": job.id,
            "tipo": job.tipo,
            "status": job.status,
            "tentativas": job.tentativas,
            "locked_by": job.locked_by,
            "criado_em": job.created_at,
            "cliente_nome": cliente_nome or "Desconhecido",
            "certidao_tipo": tipo_cert_nome or "",
            "certidao_status": certidao_status or "Desconhecido"
        })
    return result

@router.get("/pending")
def get_pending_jobs(limit: int = 10, db: Session = Depends(get_db), hub: Any = Depends(verify_worker_api_key)):
    """Busca jobs pendentes para o Worker processar e realiza o lock."""
    # Considera pending ou processing travado há mais de 10 minutos
    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    from sqlalchemy import or_
    jobs = db.query(
        Job,
        Cliente,
        Certidao,
        TipoCertidao
    ).join(Cliente, Cliente.id == Job.cliente_id).outerjoin(
        Certidao, Certidao.id == Job.certidao_id
    ).outerjoin(
        TipoCertidao, TipoCertidao.id == Certidao.tipo_certidao_id
    ).filter(
        Cliente.hub_id == hub.id,
        Job.tipo == 'emitir_certidao',
        or_(
            Job.status == 'pending',
            (Job.status == 'processing') & (Job.locked_at < ten_minutes_ago)
        )
    ).limit(limit).all()
    
    # Em um sistema real com múltiplos workers concorrentes, 
    # usaríamos FOR UPDATE SKIP LOCKED. Para simplificar no SQLAlchemy genérico:
    locked_jobs = []
    
    # O Worker que está chamando a API pode enviar seu ID, mas usaremos um genérico
    worker_id = "worker_remote" 
    
    for job, cliente, certidao, tipo_cert in jobs:
        try:
            job.status = 'processing'
            job.locked_by = worker_id
            job.locked_at = datetime.now(timezone.utc)
            db.commit()

            if not cliente or not tipo_cert:
                job.status = 'error'
                db.commit()
                continue
                
            locked_jobs.append({
                "job_id": job.id,
                "tipo": job.tipo,
                "cliente_id": cliente.id,
                "cnpj": cliente.cnpj,
                "razao_social": cliente.razao_social,
                "tipo_certidao_id": tipo_cert.id,
                "automator_module": tipo_cert.automator_module,
                "url": tipo_cert.url
            })
            
        except Exception as e:
            db.rollback()
            continue
            
    return locked_jobs

@router.post("/{job_id}/status")
def update_job_status(
    job_id: str,
    status: str = Body(..., embed=True),
    mensagem_erro: str = Body(None, embed=True),
    db: Session = Depends(get_db),
    hub: Any = Depends(verify_worker_api_key)
):
    """Atualiza o status de um Job processado pelo Worker e também da Certidão."""
    job = db.query(Job).join(Cliente).filter(Job.id == job_id, Cliente.hub_id == hub.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
        
    if status == "error":
        job.tentativas += 1
        
        # Verifica erro fatal (CNPJ Inválido)
        is_fatal_error = False
        if mensagem_erro:
            msg_lower = mensagem_erro.lower()
            if "cnpj" in msg_lower and ("inválido" in msg_lower or "invalido" in msg_lower):
                is_fatal_error = True
            
        if job.tentativas < 3 and not is_fatal_error:
            job.status = "pending" # Volta para a fila de processamento
            # Reseta o lock para poder ser pego novamente
            job.locked_by = None
            job.locked_at = None
        else:
            job.status = "error" # Esgotou as tentativas ou é erro fatal
    else:
        job.status = status
        
    try:
        db.commit()
    except Exception:
        db.rollback()
        
    # Sincroniza o status da certidão com o status do job
    if job.certidao_id:
        certidao = db.query(Certidao).filter(Certidao.id == job.certidao_id).first()
        if certidao:
            certidao.status = job.status
            try:
                db.commit()
            except Exception:
                db.rollback()

    return {"message": "Status do job atualizado com sucesso", "job_id": job_id, "status": job.status}
