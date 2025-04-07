from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import openai
import sqlite3
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

# Inicializa variáveis de tempo para assinatura
agora = datetime.now()
inicio = agora.strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
fim = (agora + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
ACCESS_TOKEN = 'TEST-5858193927098300-040318-fbc4451721a6ac67552ba0cd96b97f12-2367358847'

# Inicia o app
app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Carrega .env
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Caminho do banco
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'usuarios.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Importa funções do db.py
try:
    from db import (
        registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas,
        carregar_mensagem, renomear_conversa, excluir_conversa
    )
except ImportError as e:
    print(f"Erro ao importar funções de 'db.py': {e}")
    registrar_conversa = salvar_mensagem = carregar_conversas_ordenadas = carregar_mensagem = renomear_conversa = excluir_conversa = None

# Modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    cpf = db.Column(db.String(14))
    data_nascimento = db.Column(db.String(10))

class Assinatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    preapproval_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100))
    status = db.Column(db.String(50))
    data_inicio = db.Column(db.String(50))
    data_fim = db.Column(db.String(50))
    plano = db.Column(db.String(100))

# Função de cadastro
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        data_nascimento = request.form['data_nascimento']

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return "Usuário ou e-mail já cadastrado."

        novo_usuario = User(
            username=username,
            email=email,
            password=password,
            telefone=telefone,
            cpf=cpf,
            data_nascimento=data_nascimento
        )
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('cadastrar.html')

# Rota de login (por email OU username)
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form['username']  # Pode ser usuário ou e-mail
        password = request.form['password']

        user = User.query.filter(
            (User.username == user_input) | (User.email == user_input),
            User.password == password
        ).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username

            assinatura = Assinatura.query.filter_by(user_id=user.id).first()
            if assinatura:
                return redirect(url_for('index'))
            else:
                return redirect(url_for('pagina_assinatura'))
        else:
            error = 'Usuário, e-mail ou senha incorretos'

    return render_template('index.html', error=error)


# Página de redirecionamento para assinatura
@app.route('/pagina-assinatura')
def pagina_assinatura():
    return render_template('pagina_assinatura.html')

# Rota principal
@app.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')

    assinatura = None
    if user_id:
        assinatura = Assinatura.query.filter_by(user_id=user_id).first()

    return render_template('paginaUnica.html', username=username, user_id=user_id, tem_assinatura=bool(assinatura))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Gera imagem com DALL-E
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

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida"}), 400

        if data.get("type") == "preapproval":
            preapproval_id = data.get("data", {}).get("id")

            # Pega os detalhes da assinatura com o ID recebido
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }
            url = f"https://api.mercadopago.com/preapproval/{preapproval_id}"
            response = requests.get(url, headers=headers)
            result = response.json()

            if "payer_email" in result:
                email = result["payer_email"]
                user = User.query.filter_by(email=email).first()

                if user:
                    assinatura_existente = Assinatura.query.filter_by(preapproval_id=preapproval_id).first()
                    if not assinatura_existente:
                        nova_assinatura = Assinatura(
                            user_id=user.id,
                            preapproval_id=preapproval_id,
                            email=email,
                            status=result.get("status", "pendente"),
                            data_inicio=result.get("auto_recurring", {}).get("start_date"),
                            data_fim=result.get("auto_recurring", {}).get("end_date"),
                            plano=result.get("reason", "Assinatura")
                        )
                        db.session.add(nova_assinatura)
                        db.session.commit()
                        print("✅ Assinatura registrada para:", email)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Erro no webhook:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
