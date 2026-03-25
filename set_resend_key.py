import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.base import Configuracao

def set_resend_key():
    db = SessionLocal()
    try:
        # Check if it exists
        config = db.query(Configuracao).filter(Configuracao.chave == "resend_api_key").first()
        if config:
            config.valor = "re_W4EQDGsL_QCxQHxehJYJDcue8UCgfZtMx"
        else:
            config = Configuracao(chave="resend_api_key", valor="re_W4EQDGsL_QCxQHxehJYJDcue8UCgfZtMx", descricao="Resend API Key para envio de e-mails")
            db.add(config)
        
        db.commit()
        print("Resend API Key configurada com sucesso no banco de dados!")
    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    set_resend_key()
