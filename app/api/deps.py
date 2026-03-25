from fastapi import Request, HTTPException, status, Depends, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.base import Usuario, Hub
from app.core.security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_worker_api_key(api_key: str = Security(api_key_header), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=403, detail="API Key is missing")
    hub = db.query(Hub).filter(Hub.api_key == api_key).first()
    if not hub:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return hub

class CurrentUser(BaseModel):
    id: Optional[str] = None
    role: str = "master"
    hub_ids: List[str] = []
    cliente_ids: List[str] = []

def get_current_user(request: Request, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> CurrentUser:
    user_id = None
    
    # Try to extract user_id from token first
    if token:
        payload = verify_token(token)
        if payload and "sub" in payload:
            user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido")

    return CurrentUser(
        id=str(user.id),
        role=user.role.lower(),
        hub_ids=[str(h.id) for h in user.hubs],
        cliente_ids=[str(c.id) for c in user.clientes]
    )

def require_master(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != "master":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada. Requer perfil master.")
    return current_user
