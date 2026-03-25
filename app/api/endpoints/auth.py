import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_verification_token, verify_token, create_password_reset_token, get_password_hash
from app.core.email import send_password_reset_email_async, send_verification_email_async
from app.models.base import Usuario, Configuracao
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str
    permissions: Dict[str, bool]

class EmailVerificationRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ResendVerificationRequest(BaseModel):
    email: str

def parse_config_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return None

def get_role_permissions(db: Session, role: str) -> Dict[str, bool]:
    defaults = {
        "master": {
            "access_dashboard": True,
            "access_clientes": True,
            "access_certidoes": True,
            "access_admin": True,
            "access_logs": True,
            "create_cliente": True,
            "edit_cliente": True,
            "inactivate_cliente": True,
            "import_certidoes": True,
            "emitir_certidao": True,
            "manage_users": True,
            "manage_hubs": True,
            "manage_worker_config": True
        },
        "admin": {
            "access_dashboard": True,
            "access_clientes": True,
            "access_certidoes": True,
            "access_admin": True,
            "access_logs": False,
            "create_cliente": True,
            "edit_cliente": True,
            "inactivate_cliente": True,
            "import_certidoes": True,
            "emitir_certidao": True,
            "manage_users": True,
            "manage_hubs": False,
            "manage_worker_config": False
        },
        "cliente": {
            "access_dashboard": True,
            "access_clientes": True,
            "access_certidoes": True,
            "access_admin": False,
            "access_logs": False,
            "create_cliente": False,
            "edit_cliente": False,
            "inactivate_cliente": False,
            "import_certidoes": True,
            "emitir_certidao": True,
            "manage_users": False,
            "manage_hubs": False,
            "manage_worker_config": False
        }
    }
    role_key = role.lower()
    permissions = defaults.get(role_key, {}).copy()
    if not permissions:
        return {}
    prefix = f"perm_{role_key}_"
    configs = db.query(Configuracao).filter(Configuracao.chave.like(f"{prefix}%")).all()
    for config in configs:
        perm_key = config.chave.replace(prefix, "", 1)
        parsed_value = parse_config_bool(config.valor)
        if parsed_value is not None:
            permissions[perm_key] = parsed_value
    return permissions

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    try:
        user = db.query(Usuario).filter(Usuario.email == form_data.username).first()
        if not user:
            raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
        if not verify_password(form_data.password, user.senha_hash):
            raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
        if not user.ativo:
            raise HTTPException(status_code=400, detail="Usuário inativo")
        if not user.email_verified:
            raise HTTPException(status_code=403, detail="E-mail não verificado. Por favor, verifique seu e-mail antes de fazer login.")

        permissions = get_role_permissions(db, user.role)
        return {
            "access_token": create_access_token(str(user.id)),
            "token_type": "bearer",
            "user_id": str(user.id),
            "role": user.role,
            "permissions": permissions
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

@router.post("/verify-email")
def verify_email(data: EmailVerificationRequest, db: Session = Depends(get_db)):
    payload = verify_token(data.token)
    if not payload or payload.get("type") != "verification":
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
        
    email = payload.get("sub")
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    if user.email_verified:
        return {"msg": "E-mail já verificado anteriormente"}
        
    user.email_verified = True
    db.commit()
    return {"msg": "E-mail verificado com sucesso"}

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Run DB queries in threadpool if needed, but for simple queries it's usually fine
    user = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not user:
        # Retorna mensagem genérica por segurança
        return {"msg": "Se o e-mail estiver cadastrado, você receberá um link para redefinir a senha."}
        
    token = create_password_reset_token(user.email)
    
    # Run the email sending as an independent task that does not block the response
    # This bypasses the Starlette BaseHTTPMiddleware BackgroundTasks bug
    asyncio.create_task(send_password_reset_email_async(user.email, token))
    
    return {"msg": "Se o e-mail estiver cadastrado, você receberá um link para redefinir a senha."}

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = verify_token(data.token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
        
    email = payload.get("sub")
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    user.senha_hash = get_password_hash(data.new_password)
    db.commit()
    return {"msg": "Senha redefinida com sucesso"}

@router.post("/resend-verification")
async def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not user:
        return {"msg": "Se o e-mail estiver cadastrado, você receberá um novo link de verificação."}

    if user.email_verified:
        return {"msg": "E-mail já verificado anteriormente."}

    token = create_verification_token(user.email)
    asyncio.create_task(send_verification_email_async(user.email, token))
    return {"msg": "Se o e-mail estiver cadastrado, você receberá um novo link de verificação."}
