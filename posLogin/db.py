import sqlite3

def criar_banco_de_dados():
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()


# Criar a tabela de conversas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

# Criar a tabela de mensagens
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversa_id INTEGER NOT NULL,
        remetente TEXT ,
        mensagem TEXT ,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(conversa_id) REFERENCES conversas(id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()

# Função para registrar uma nova conversa
def registrar_conversa(user_id, title):
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversas (user_id, title) VALUES (?, ?)", (user_id, title))
    conn.commit()
    return cursor.lastrowid

# Função para salvar mensagens
def salvar_mensagem(conversa_id, remetente, mensagem):
    try:
        conn = sqlite3.connect('historico.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mensagens (conversa_id, remetente, mensagem) VALUES (?, ?, ?)",
                       (conversa_id, remetente, mensagem))
        conn.commit()  # Garante que a transação é confirmada
        print(f"Mensagem salva: {mensagem}")
    except Exception as e:
        print(f"Erro ao salvar mensagem: {str(e)}")
    finally:
        conn.close()

# Função para carregar as conversas de um usuário
def carregar_conversas(user_id):
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM conversas WHERE user_id = ?", (user_id,))
    conversas = cursor.fetchall()
    conn.close()
    return conversas

# Função para carregar o histórico de mensagens de uma conversa específica
def carregar_mensagem(conversa_id):
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()
    cursor.execute("SELECT remetente, mensagem FROM mensagens WHERE conversa_id = ? ORDER BY data_hora ASC", (conversa_id,))
    historico = cursor.fetchall()
    conn.close()
    return [{"remetente": msg[0], "mensagem": msg[1]} for msg in historico]

# Função para renomear uma conversa
def renomear_conversa(conversa_id, novo_titulo):
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE conversas SET title = ? WHERE id = ?", (novo_titulo, conversa_id))
    conn.commit()
    conn.close()

# Função para excluir uma conversa e suas mensagens
def excluir_conversa(conversa_id):
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mensagens WHERE conversa_id = ?", (conversa_id,))
    cursor.execute("DELETE FROM conversas WHERE id = ?", (conversa_id,))
    conn.commit()
    conn.close()

# Criar o banco de dados na primeira execução
criar_banco_de_dados()

# Função para carregar as conversas de um usuário ordenadas pela última mensagem
def carregar_conversas_ordenadas(user_id):
    conn = sqlite3.connect('historico.db')
    cursor = conn.cursor()

    # Seleciona as conversas e busca a última mensagem enviada em cada conversa
    cursor.execute('''
        SELECT conversas.id, conversas.title, MAX(mensagens.data_hora) AS ultima_modificacao
        FROM conversas
        JOIN mensagens ON mensagens.conversa_id = conversas.id
        WHERE conversas.user_id = ?
        GROUP BY conversas.id
        ORDER BY ultima_modificacao DESC
    ''', (user_id,))
    
    conversas = cursor.fetchall()
    conn.close()
    return conversas
