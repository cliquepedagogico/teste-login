from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
DB_URI = os.getenv("DB_URI")  # esse é o banco das conversas

# Cria engine e conexão
engine = create_engine(DB_URI)

with engine.connect() as connection:
    try:
        # Tenta adicionar a coluna 'titulo'
        connection.execute(text("ALTER TABLE conversas ADD COLUMN titulo VARCHAR(255);"))
        print("✅ Coluna 'titulo' adicionada com sucesso.")
    except Exception as e:
        print("⚠️ Erro ao alterar tabela:", e)
