from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from app.core.database import get_db
from app.models.base import Cliente, Certidao, Job, Hub
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
        
        # Atividades recentes baseadas nos jobs mais novos
        recent_jobs = q_jobs.order_by(Job.created_at.desc()).limit(5).all()
        from app.models.base import TipoCertidao
        atividades_recentes = []
        for j in recent_jobs:
            cliente = db.query(Cliente).filter(Cliente.id == j.cliente_id).first()
            cliente_nome = cliente.razao_social if cliente else "Sistema"
            
            tipo_nome = j.tipo
            if j.certidao_id:
                cert = db.query(Certidao).filter(Certidao.id == j.certidao_id).first()
                if cert:
                    tipo_cert = db.query(TipoCertidao).filter(TipoCertidao.id == cert.tipo_certidao_id).first()
                    if tipo_cert:
                        tipo_nome = tipo_cert.nome
                        
            atividades_recentes.append({
                "id": str(j.id),
                "status": j.status,
                "tipo": tipo_nome,
                "cliente": cliente_nome,
                "time": j.created_at.strftime("%H:%M") if j.created_at else "00:00"
            })
        
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
