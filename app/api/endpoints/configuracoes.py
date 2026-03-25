from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.base import Configuracao
from pydantic import BaseModel

router = APIRouter()

class ConfiguracaoBase(BaseModel):
    chave: str
    valor: str
    descricao: str | None = None

class ConfiguracaoResponse(ConfiguracaoBase):
    id: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ConfiguracaoResponse])
def listar_configuracoes(db: Session = Depends(get_db)):
    return db.query(Configuracao).all()

@router.post("/batch", response_model=Dict[str, str])
def salvar_configuracoes_batch(configuracoes: Dict[str, str], db: Session = Depends(get_db)):
    for chave, valor in configuracoes.items():
        config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
        if config:
            config.valor = str(valor)
        else:
            nova_config = Configuracao(chave=chave, valor=str(valor))
            db.add(nova_config)
    db.commit()
    return {"message": "Configurações salvas com sucesso"}

@router.get("/{chave}", response_model=ConfiguracaoResponse)
def obter_configuracao(chave: str, db: Session = Depends(get_db)):
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    return config
