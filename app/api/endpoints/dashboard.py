from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from app.core.database import get_db
from app.models.base import Cliente, Certidao, Job, Hub, TipoCertidao
from app.api.deps import get_current_user, CurrentUser

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    try:
        # Base queries
        q_clientes = db.query(Cliente)
        q_certidoes = db.query(Certidao)
        q_hubs = db.query(Hub).filter(Hub.ativo == True)
        q_jobs = db.query(Job)
        
        if current_user.role == "admin" and current_user.hub_ids:
            q_clientes = q_clientes.filter(Cliente.hub_id.in_(current_user.hub_ids))
            q_certidoes = q_certidoes.join(Cliente).filter(Cliente.hub_id.in_(current_user.hub_ids))
            q_jobs = q_jobs.join(Cliente).filter(Cliente.hub_id.in_(current_user.hub_ids))
        elif current_user.role == "cliente" and current_user.cliente_ids:
            q_clientes = q_clientes.filter(Cliente.id.in_(current_user.cliente_ids))
            q_certidoes = q_certidoes.filter(Certidao.cliente_id.in_(current_user.cliente_ids))
            q_jobs = q_jobs.filter(Job.cliente_id.in_(current_user.cliente_ids))

        total_clientes = q_clientes.count()
        certidoes_emitidas = q_certidoes.filter(Certidao.status == "completed").count()
        hubs_ativos = q_hubs.count() if current_user.role == "master" else (1 if current_user.role == "admin" else 0)
        
        processamento_hoje = q_jobs.filter(Job.status.in_(["pending", "processing", "completed", "error"])).count()
        com_erro = q_jobs.filter(Job.status == "error").count()
        
        recent_jobs_query = (
            db.query(
                Job.id,
                Job.status,
                Job.tipo,
                Job.created_at,
                Cliente.razao_social.label("cliente_nome"),
                TipoCertidao.nome.label("tipo_cert_nome")
            )
            .outerjoin(Cliente, Cliente.id == Job.cliente_id)
            .outerjoin(Certidao, Certidao.id == Job.certidao_id)
            .outerjoin(TipoCertidao, TipoCertidao.id == Certidao.tipo_certidao_id)
        )
        if current_user.role == "admin" and current_user.hub_ids:
            recent_jobs_query = recent_jobs_query.filter(Cliente.hub_id.in_(current_user.hub_ids))
        elif current_user.role == "cliente" and current_user.cliente_ids:
            recent_jobs_query = recent_jobs_query.filter(Job.cliente_id.in_(current_user.cliente_ids))
        recent_jobs = recent_jobs_query.order_by(Job.created_at.desc()).limit(5).all()
        atividades_recentes = [
            {
                "id": str(job_id),
                "status": status,
                "tipo": tipo_cert_nome or tipo,
                "cliente": cliente_nome or "Sistema",
                "time": created_at.strftime("%H:%M") if created_at else "00:00"
            }
            for job_id, status, tipo, created_at, cliente_nome, tipo_cert_nome in recent_jobs
        ]
        
        total_jobs = q_jobs.count()
        completed_jobs = q_jobs.filter(Job.status == "completed").count()
        percentage = 0 if total_jobs == 0 else int((completed_jobs / total_jobs) * 100)
        
        return {
            "total_clientes": total_clientes,
            "certidoes_emitidas": certidoes_emitidas,
            "hubs_ativos": hubs_ativos,
            "processamento_hoje": processamento_hoje,
            "com_erro": com_erro,
            "percentage": percentage,
            "atividades_recentes": atividades_recentes
        }
    except Exception as e:
        import logging
        logging.error(f"Dashboard endpoint error: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Internal server error")
