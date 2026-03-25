from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.base import TipoCertidao

router = APIRouter()

@router.get("/")
def listar_tipos_certidao(db: Session = Depends(get_db)):
    tipos = db.query(TipoCertidao).filter(TipoCertidao.ativo == True).all()
    return [
        {
            "id": t.id,
            "nome": t.nome,
            "url": t.url,
            "possui_captcha": t.possui_captcha,
            "tipo_captcha": t.tipo_captcha,
            "automator_module": t.automator_module
        } for t in tipos
    ]
