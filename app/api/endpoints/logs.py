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

    query = (
        db.query(
            Job,
            Cliente.razao_social.label("cliente_nome"),
            TipoCertidao.nome.label("tipo_cert_nome")
        )
        .join(Cliente, Cliente.id == Job.cliente_id)
        .outerjoin(Certidao, Certidao.id == Job.certidao_id)
        .outerjoin(TipoCertidao, TipoCertidao.id == Certidao.tipo_certidao_id)
        .order_by(Job.created_at.desc())
    )
    
    if status:
        query = query.filter(Job.status == status)
        
    jobs = query.limit(limit).all()
    
    result = []
    for job, cliente_nome, tipo_cert_nome in jobs:
        result.append({
            "id": job.id,
            "tipo": job.tipo,
            "status": job.status,
            "tentativas": job.tentativas,
            "locked_by": job.locked_by,
            "locked_at": job.locked_at,
            "created_at": job.created_at,
            "cliente_id": job.cliente_id,
            "cliente_nome": cliente_nome or "Desconhecido",
            "certidao_tipo": tipo_cert_nome or "",
            "certidao_id": job.certidao_id
        })
        
    return result
