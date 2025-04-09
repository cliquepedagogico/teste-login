import sqlite3

conn = sqlite3.connect("assinaturas.db")
cursor = conn.cursor()

# Apaga se já existir
cursor.execute("DROP TABLE IF EXISTS assinaturas")

# Cria com CPF único
cursor.execute("""
CREATE TABLE assinaturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    telefone TEXT,
    cpf TEXT UNIQUE NOT NULL,
    data_nascimento TEXT,
    status TEXT DEFAULT 'nao_assinante',
    data_assinatura TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
print("✅ Tabela criada com CPF como UNIQUE.")
