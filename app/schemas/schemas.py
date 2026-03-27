from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ClienteBase(BaseModel):
    cnpj: str
    razao_social: str
    telefone: Optional[str] = None
    email: Optional[str] = None
    responsavel: Optional[str] = None
    ativo: Optional[bool] = True

class ClienteCreate(ClienteBase):
    hub_id: Optional[str] = None
    tipos_certidoes: Optional[List[str]] = []

class ClienteUpdate(ClienteBase):
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    tipos_certidoes: Optional[List[str]] = []
    hub_id: Optional[str] = None

class ClienteResponse(ClienteBase):
    id: UUID
    hub_id: Optional[UUID] = None
    created_at: datetime
    tipos_certidoes: Optional[List[str]] = []
    model_config = ConfigDict(from_attributes=True)

class CertidaoBase(BaseModel):
    cliente_id: UUID
    tipo_certidao_id: UUID
    status: str
    caminho_arquivo: Optional[str] = None
    mensagem_erro: Optional[str] = None

class CertidaoResponse(CertidaoBase):
    id: UUID
    criado_em: datetime
    atualizado_em: datetime
    model_config = ConfigDict(from_attributes=True)

class UsuarioBase(BaseModel):
    nome: str
    email: str
    telefone: Optional[str] = None
    role: str = "Operador"
    ativo: Optional[bool] = True

class UsuarioCreate(UsuarioBase):
    senha: str
    hub_id: Optional[str] = None # Mantido por compatibilidade
    cliente_id: Optional[str] = None # Mantido por compatibilidade
    hub_ids: Optional[List[str]] = []
    cliente_ids: Optional[List[str]] = []

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    role: Optional[str] = None
    senha: Optional[str] = None
    ativo: Optional[bool] = None
    hub_id: Optional[str] = None
    cliente_id: Optional[str] = None
    hub_ids: Optional[List[str]] = []
    cliente_ids: Optional[List[str]] = []

class UsuarioResponse(UsuarioBase):
    id: UUID
    hub_id: Optional[UUID] = None
    cliente_id: Optional[UUID] = None
    hub_ids: Optional[List[str]] = []
    cliente_ids: Optional[List[str]] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
