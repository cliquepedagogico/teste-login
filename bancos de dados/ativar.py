import sqlite3

conn = sqlite3.connect('sistema_assinaturas.db')
cursor = conn.cursor()

cursor.execute("""
    UPDATE assinatura
    SET status = 'ativa'
    WHERE email = 'teste@gmail.com'
""")

conn.commit()
conn.close()

print("✅ Status atualizado com sucesso!")
