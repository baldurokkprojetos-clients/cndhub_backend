from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Table, LargeBinary
import uuid
from datetime import datetime
from app.core.database import Base
from sqlalchemy.orm import relationship

# Para compatibilidade com SQLite, usamos String(36) para armazenar UUIDs
def get_uuid():
    return str(uuid.uuid4())

usuario_hubs = Table(
    'usuario_hubs',
    Base.metadata,
    Column('usuario_id', String(36), ForeignKey('usuarios.id', ondelete="CASCADE"), primary_key=True),
    Column('hub_id', String(36), ForeignKey('hubs.id', ondelete="CASCADE"), primary_key=True)
)

usuario_clientes = Table(
    'usuario_clientes',
    Base.metadata,
    Column('usuario_id', String(36), ForeignKey('usuarios.id', ondelete="CASCADE"), primary_key=True),
    Column('cliente_id', String(36), ForeignKey('clientes.id', ondelete="CASCADE"), primary_key=True)
)

class Hub(Base):
    __tablename__ = "hubs"
    id = Column(String(36), primary_key=True, default=get_uuid)
    nome = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    clientes = relationship("Cliente", back_populates="hub")
    usuarios = relationship("Usuario", secondary=usuario_hubs, back_populates="hubs")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String(36), primary_key=True, default=get_uuid)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    telefone = Column(String(50))
    senha_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # master, admin, cliente
    hub_id = Column(String(36), ForeignKey("hubs.id"), nullable=True) # Mantido para retrocompatibilidade
    cliente_id = Column(String(36), ForeignKey("clientes.id"), nullable=True) # Mantido para retrocompatibilidade
    ativo = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    hubs = relationship("Hub", secondary=usuario_hubs, back_populates="usuarios")
    clientes = relationship("Cliente", secondary=usuario_clientes, back_populates="usuarios")

    @property
    def hub_ids(self):
        return [str(hub.id) for hub in self.hubs]

    @property
    def cliente_ids(self):
        return [str(cliente.id) for cliente in self.clientes]

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(String(36), primary_key=True, default=get_uuid)
    hub_id = Column(String(36), ForeignKey("hubs.id"))
    cnpj = Column(String(20), index=True, nullable=False)
    razao_social = Column(String(255), nullable=False)
    telefone = Column(String(50))
    email = Column(String(255))
    responsavel = Column(String(255))
    api_key = Column(String(255))
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    hub = relationship("Hub", back_populates="clientes")
    jobs = relationship("Job", back_populates="cliente")
    usuarios = relationship("Usuario", secondary=usuario_clientes, back_populates="clientes")

class TipoCertidao(Base):
    __tablename__ = "tipo_certidoes"
    id = Column(String(36), primary_key=True, default=get_uuid)
    nome = Column(String(255), nullable=False)
    url = Column(Text)
    possui_captcha = Column(Boolean, default=False)
    tipo_captcha = Column(String(50), default="none")
    automator_module = Column(String(255), nullable=False) # Identificador modular para o Worker
    ativo = Column(Boolean, default=True)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True, default=get_uuid)
    tipo = Column(String(50), nullable=False, index=True) # criar_pasta, emitir_certidao
    cliente_id = Column(String(36), ForeignKey("clientes.id"), index=True)
    certidao_id = Column(String(36), ForeignKey("certidoes.id"), nullable=True, index=True)
    status = Column(String(50), default="pending", index=True)
    tentativas = Column(Integer, default=0)
    locked_by = Column(String(255), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    cliente = relationship("Cliente", back_populates="jobs")

class Certidao(Base):
    __tablename__ = "certidoes"
    id = Column(String(36), primary_key=True, default=get_uuid)
    cliente_id = Column(String(36), ForeignKey("clientes.id"), index=True)
    tipo_certidao_id = Column(String(36), ForeignKey("tipo_certidoes.id"), index=True)
    status = Column(String(50), default="pending", index=True)
    caminho_arquivo = Column(Text)
    arquivo_conteudo = Column(LargeBinary, nullable=True)
    tentativa = Column(Integer, default=0)
    mensagem_erro = Column(Text)
    worker_id = Column(String(255))
    criado_em = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    atualizado_em = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('cliente_id', 'tipo_certidao_id', name='uq_cliente_tipo_certidao'),
    )

class Configuracao(Base):
    __tablename__ = "configuracoes"
    id = Column(String(36), primary_key=True, default=get_uuid)
    chave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(Text, nullable=False)
    descricao = Column(String(255))
    atualizado_em = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
