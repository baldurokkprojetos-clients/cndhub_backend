from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.base import Hub
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from app.api.deps import get_current_user, CurrentUser

router = APIRouter()

class HubCreate(BaseModel):
    nome: str
    ativo: Optional[bool] = True

class HubUpdate(BaseModel):
    nome: Optional[str] = None
    ativo: Optional[bool] = None

class HubResponse(BaseModel):
    id: UUID
    nome: str
    ativo: bool
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[HubResponse])
def listar_hubs(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    query = db.query(Hub)
    if current_user.role == "admin":
        query = query.filter(Hub.id.in_(current_user.hub_ids))
    elif current_user.role == "cliente":
        return []
    return query.all()

@router.post("/", response_model=HubResponse)
def criar_hub(hub: HubCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
    import uuid
    new_hub = Hub(nome=hub.nome, ativo=hub.ativo, api_key=str(uuid.uuid4()))
    db.add(new_hub)
    db.commit()
    db.refresh(new_hub)
    return new_hub

@router.put("/{hub_id}", response_model=HubResponse)
def atualizar_hub(hub_id: str, hub: HubUpdate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
    db_hub = db.query(Hub).filter(Hub.id == hub_id).first()
    if not db_hub:
        raise HTTPException(status_code=404, detail="Hub não encontrada")
    
    update_data = hub.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_hub, key, value)
        
    db.commit()
    db.refresh(db_hub)
    return db_hub

@router.delete("/{hub_id}")
def deletar_hub(hub_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Acesso negado")
    db_hub = db.query(Hub).filter(Hub.id == hub_id).first()
    if not db_hub:
        raise HTTPException(status_code=404, detail="Hub não encontrada")
    db.delete(db_hub)
    db.commit()
    return {"message": "Hub deletada com sucesso"}
