from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import openai
import sqlite3
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
agora = datetime.now()
inicio = agora.strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
fim = (agora + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")

# Importa funções do arquivo db.py
try:
    from db import (
        registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas, 
        carregar_mensagem, renomear_conversa, excluir_conversa
    )
except ImportError as e:
    print(f"Erro ao importar funções de 'db.py': {e}")
    registrar_conversa = salvar_mensagem = carregar_conversas_ordenadas = carregar_mensagem = renomear_conversa = excluir_conversa = None

app = Flask(__name__)
app.secret_key = 'chave_secreta'
openai.api_key = os.getenv('OPENAI_API_KEY')

# Caminho absoluto do banco de dados
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'usuarios.db')

if not os.path.exists(DATABASE_PATH):
    raise FileNotFoundError(f'O banco de dados não foi encontrado em: {DATABASE_PATH}')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))  # redireciona para a página unificada

        else:
            error = 'Usuário ou senha incorretos'

    # Se for GET ou erro, mostra o formulário de login de novo
    return render_template('index.html', error=error)


# Página única com loja e chat (visibilidade baseada em login)
@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))  # Recarrega página com sessão ativa
        else:
            error = 'Usuário ou senha incorretos'

    return render_template('paginaUnica.html',
                           username=session.get('username'),
                           user_id=session.get('user_id'),
                           error=error)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 🔹 Chat com OpenAI
load_dotenv()

def gerar_imagem(descricao):
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=descricao,
            size="1024x1024",
            quality="standard",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Erro ao gerar imagem: {str(e)}"

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    try:
        data = request.json
        user_id = session['user_id']
        user_message = data.get('message')
        funcionalidade = data.get('funcionalidade')
        conversa_id = data.get('conversa_id')
        history = data.get('history', [])

        if not conversa_id:
            title = user_message[:20]
            conversa_id = registrar_conversa(user_id, title) if registrar_conversa else None

        salvar_mensagem(conversa_id, 'user', user_message) if salvar_mensagem else None

        if funcionalidade == 'gerar_imagem':
            url_imagem = gerar_imagem(user_message)
            if salvar_mensagem:
                salvar_mensagem(conversa_id, 'vix', url_imagem)
            if "Erro" in url_imagem:
                return jsonify({"response": url_imagem})
            return jsonify({"image_url": url_imagem, "conversa_id": conversa_id})

        instruction = "Aqui vai sua instrução do sistema"
        messages = [{"role": "system", "content": instruction}] + history + [{"role": "user", "content": user_message}]

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        reply = response.choices[0].message.content

        if salvar_mensagem:
            salvar_mensagem(conversa_id, 'vix', reply)

        return jsonify({"response": reply, "conversa_id": conversa_id})

    except Exception as e:
        print(f"Erro no chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/carregar_conversas', methods=['POST'])
def carregar_conversas_usuario():
    if not carregar_conversas_ordenadas:
        return jsonify({"error": "Erro ao carregar conversas"}), 500
    user_id = session.get('user_id')
    conversas = carregar_conversas_ordenadas(user_id)
    return jsonify([{"id": conv[0], "title": conv[1]} for conv in conversas])

@app.route('/carregar_mensagem', methods=['POST'])
def carregar_mensagem_view():
    try:
        conversa_id = request.json.get('conversa_id')

        if not conversa_id:
            return jsonify({"error": "Conversa ID não fornecido"}), 400

        if not carregar_mensagem:
            return jsonify({"error": "Erro ao carregar mensagens"}), 500

        historico = carregar_mensagem(conversa_id)
        return jsonify(historico)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/renomear_conversa', methods=['POST'])
def renomear():
    if not renomear_conversa:
        return jsonify({"error": "Erro ao renomear conversa"}), 500
    conversa_id = request.json.get('conversa_id')
    novo_titulo = request.json.get('novo_titulo')
    renomear_conversa(conversa_id, novo_titulo)
    return jsonify({"status": "Conversa renomeada"})

@app.route('/excluir_conversa', methods=['POST'])
def excluir_conversa_view():
    try:
        conversa_id = request.json.get('conversa_id')

        if not excluir_conversa:
            return jsonify({"error": "Erro ao excluir conversa"}), 500

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mensagens WHERE conversa_id = ?", (conversa_id,))
            cursor.execute("DELETE FROM conversas WHERE id = ?", (conversa_id,))
            conn.commit()

        return jsonify({"status": "Conversa excluída"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/carregar_historico', methods=['POST'])
def carregar_historico():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida. Nenhum JSON recebido"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID não fornecido"}), 400

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, created_at FROM conversas WHERE user_id = ?", (user_id,))
            conversas = cursor.fetchall()

            historico = []
            for conversa in conversas:
                conversa_id, title, created_at = conversa
                cursor.execute("SELECT remetente, mensagem FROM mensagens WHERE conversa_id = ?", (conversa_id,))
                mensagens = cursor.fetchall()

                historico.append({
                    "conversa_id": conversa_id,
                    "title": title,
                    "created_at": created_at,
                    "mensagens": [
                        {"remetente": msg[0], "mensagem": msg[1]} for msg in mensagens
                    ]
                })

        return jsonify(historico)

    except sqlite3.Error as db_error:
        return jsonify({"error": f"Erro no banco de dados: {str(db_error)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500
    
#pagamento
@app.route('/criar_assinatura', methods=['POST'])
def criar_assinatura():
    import requests
    from datetime import datetime, timedelta

    access_token = "APP_USR-5858193927098300-040318-cca10959729f3248f817853f80c965ab-2367358847"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    hoje = datetime.now()
    um_ano = hoje + timedelta(days=365)

    data = {
        "reason": "Assinatura Premium - Mensal",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": 0.50,
            "currency_id": "BRL",
            "start_date": inicio,
            "end_date": fim
             },
        "back_url": "https://teste-login-0hdz.onrender.com",
        "payer_email": "rrdsju@email.com" 
    }

    response = requests.post("https://api.mercadopago.com/preapproval", json=data, headers=headers)
    print("🔍 STATUS:", response.status_code)
    print("📦 RESPOSTA:", response.json())  # isso vai mostrar o erro real da API

    result = response.json()

    if "init_point" in result:
        return redirect(result["init_point"])
    else:
        return f"Erro na criação da assinatura:<br>{result}"
@app.route('/obrigado')
def obrigado():
    return "Obrigado pela assinatura! Acesso liberado com sucesso!"



if __name__ == '__main__':
    app.run(debug=True)
