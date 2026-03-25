from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.security import verify_token
from app.core.database import SessionLocal
from app.models.base import Usuario
from app.api.endpoints import clientes, certidoes, jobs, tipos_certidao, dashboard, usuarios, configuracoes, hubs, logs, auth

from fastapi.staticfiles import StaticFiles
import os

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
    )

    # Configuração de CORS para segurança e integração com o Frontend (Next.js)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # TODO: Restringir em produção
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    @app.middleware("http")
    async def role_based_access_middleware(request: Request, call_next):
        path = request.url.path
        
        # Ignorar validação para rotas públicas ou arquivos estáticos
        if not path.startswith("/api/v1/") or path.startswith("/api/v1/health") or path.startswith("/api/v1/auth"):
            return await call_next(request)
            
        role = request.headers.get("X-User-Role", "master").lower()
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            payload = verify_token(token)
            if payload and "sub" in payload and SessionLocal is not None:
                db = SessionLocal()
                try:
                    user = db.query(Usuario).filter(Usuario.id == payload.get("sub")).first()
                    if user:
                        role = user.role.lower()
                finally:
                    db.close()
        method = request.method
        
        # Cliente apenas visualiza dados vinculados (exemplo simplificado)
        if role == "cliente":
            forbidden_paths = ["/api/v1/configuracoes", "/api/v1/hubs"]
            if any(path.startswith(p) for p in forbidden_paths):
                return JSONResponse(status_code=403, content={"detail": "Acesso negado. Cliente não pode acessar estas configurações."})
            # Restringir ações de escrita para clientes, exceto possivelmente solicitar certidões e gerenciar usuários
            if method in ["POST", "PUT", "DELETE"] and not path.startswith("/api/v1/jobs") and not path.startswith("/api/v1/usuarios"):
                return JSONResponse(status_code=403, content={"detail": "Acesso negado. Cliente apenas visualiza os dados ou gerencia usuários/jobs."})
                
        # Admin gere HUB e clientes, mas não configurações do sistema master
        if role == "admin":
            if path.startswith("/api/v1/configuracoes"):
                return JSONResponse(status_code=403, content={"detail": "Acesso negado. Apenas Master pode alterar configurações globais."})

        response = await call_next(request)
        return response

    # Criar diretório de storage se não existir
    os.makedirs("storage/certidoes", exist_ok=True)
    app.mount("/storage", StaticFiles(directory="storage"), name="storage")

    @app.get("/health", tags=["Health"])
    def health_check():
        return {
            "status": "ok", 
            "project": settings.PROJECT_NAME, 
            "version": settings.VERSION
        }

    # Rotas
    app.include_router(clientes.router, prefix="/api/v1/clientes", tags=["Clientes"])
    app.include_router(certidoes.router, prefix="/api/v1/certidoes", tags=["Certidões"])
    app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
    app.include_router(tipos_certidao.router, prefix="/api/v1/tipos-certidao", tags=["Tipos de Certidão"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    app.include_router(usuarios.router, prefix="/api/v1/usuarios", tags=["Usuários"])
    app.include_router(configuracoes.router, prefix="/api/v1/configuracoes", tags=["Configurações"])
    app.include_router(hubs.router, prefix="/api/v1/hubs", tags=["Hubs"])
    app.include_router(logs.router, prefix="/api/v1/logs", tags=["Logs"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

    return app

app = create_app()
