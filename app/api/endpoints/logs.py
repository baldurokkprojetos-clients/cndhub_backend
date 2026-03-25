from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, CurrentUser
from app.models.base import Job, Cliente, Certidao, TipoCertidao
from typing import List, Dict, Any, Optional

router = APIRouter()

@router.get("/")
def listar_logs_jobs(
    limit: int = Query(50, description="Número máximo de registros"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Lista os logs de jobs e atividades.
    Acesso restrito a usuários Master.
    """
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas usuários Master podem visualizar os logs.")

    query = db.query(Job).order_by(Job.created_at.desc())
    
    if status:
        query = query.filter(Job.status == status)
        
    jobs = query.limit(limit).all()
    
    result = []
    for job in jobs:
        cliente = db.query(Cliente).filter(Cliente.id == job.cliente_id).first()
        certidao = db.query(Certidao).filter(Certidao.id == job.certidao_id).first()
        tipo_cert_nome = ""
        if certidao:
            tipo_cert = db.query(TipoCertidao).filter(TipoCertidao.id == certidao.tipo_certidao_id).first()
            if tipo_cert:
                tipo_cert_nome = tipo_cert.nome

        result.append({
            "id": job.id,
            "tipo": job.tipo,
            "status": job.status,
            "tentativas": job.tentativas,
            "locked_by": job.locked_by,
            "locked_at": job.locked_at,
            "created_at": job.created_at,
            "cliente_id": job.cliente_id,
            "cliente_nome": cliente.razao_social if cliente else "Desconhecido",
            "certidao_tipo": tipo_cert_nome,
            "certidao_id": job.certidao_id
        })
        
    return result