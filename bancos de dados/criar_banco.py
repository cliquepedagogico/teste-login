# import sqlite3

# conn = sqlite3.connect("sistema_assinaturas.db")
# cursor = conn.cursor()

# # Renomeia a tabela antiga
# cursor.execute("ALTER TABLE assinatura RENAME TO assinatura_antiga")

# # Cria a nova tabela sem o campo usuario_id
# cursor.execute("""
# CREATE TABLE assinatura (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     preapproval_id TEXT,
#     status TEXT,
#     data_inicio TEXT,
#     data_expiracao TEXT,
#     username TEXT,
#     email TEXT,
#     senha TEXT,
#     telefone TEXT,
#     cpf TEXT,
#     data_nascimento TEXT
# );
# """)

# # Copia os dados da tabela antiga (exceto usuario_id)
# cursor.execute("""
# INSERT INTO assinatura (id, preapproval_id, status, data_inicio, data_expiracao,
#                         username, email, senha, telefone, cpf, data_nascimento)
# SELECT id, preapproval_id, status, data_inicio, data_expiracao,
#        username, email, senha, telefone, cpf, data_nascimento
# FROM assinatura_antiga;
# """)

# # Remove a tabela antiga
# cursor.execute("DROP TABLE assinatura_antiga")

# conn.commit()
# conn.close()
# print("✅ Campo 'usuario_id' removido com sucesso.")


# import sqlite3

# # Troque aqui pelo e-mail que você quer autorizar
# EMAIL_DO_USUARIO = "exemplo@email.com"

# conn = sqlite3.connect("sistema_assinaturas.db")
# cursor = conn.cursor()

# cursor.execute("""
#     UPDATE assinatura
#     SET status = 'authorized', data_inicio = datetime('now')
#     WHERE email = ?
# """, ('teste@gmail.com',))

# conn.commit()
# conn.close()

# print(f"✅ Usuário {EMAIL_DO_USUARIO} agora está com assinatura 'authorized'.")
# import sqlite3
# conn = sqlite3.connect('sistema_assinaturas.db')
# cursor = conn.cursor()
# cursor.execute("ALTER TABLE assinatura ADD COLUMN stripe_subscription_id TEXT;")
# conn.commit()
# conn.close()
# print("Coluna adicionada com sucesso.")
# import sqlite3

# conn = sqlite3.connect('sistema_assinaturas.db')
# cursor = conn.cursor()
# cursor.execute("ALTER TABLE assinatura ADD COLUMN mercado_pago_id TEXT")
# conn.commit()
# conn.close()
# print("✅ Coluna 'mercado_pago_id' adicionada com sucesso.")


# import sqlite3

# # Conecta ao banco de dados
# conn = sqlite3.connect('sistema_assinaturas.db')
# cursor = conn.cursor()

# # Deleta todos os usuários cujo status não seja 'ativa'
# cursor.execute("""
#     DELETE FROM assinatura
#     WHERE status IS NULL OR status == 'ativa'
# """)

# # Confirma a exclusão
# conn.commit()
# conn.close()

# print("🗑️ Usuários com status diferente de 'ativa' foram removidos com sucesso.")
