from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import openai
import sqlite3
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
from models import db, User, Assinatura  


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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Arquivo local
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)



# Importa funções do db.py
try:
    from db import (
        registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas,
        carregar_mensagem, renomear_conversa, excluir_conversa
    )
except ImportError as e:
    print(f"Erro ao importar funções de 'db.py': {e}")
    registrar_conversa = salvar_mensagem = carregar_conversas_ordenadas = carregar_mensagem = renomear_conversa = excluir_conversa = None


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

# Página de assinatura personalizada
@app.route('/pagina-assinatura')
def pagina_assinatura():
    return render_template('pagina_assinatura.html')

@app.route('/assinatura', methods=['POST'])
def assinatura():
    return redirect(url_for('pagina_assinatura'))

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form['username']
        password = request.form['password']

        user = User.query.filter(
            (User.username == user_input) | (User.email == user_input),
            User.password == password
        ).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            error = 'Usuário, e-mail ou senha incorretos'

    return render_template('index.html', error=error)

# Rota principal
@app.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')
    tem_assinatura = False

    if user_id:
        assinatura = Assinatura.query.filter_by(user_id=user_id, status='authorized').first()
        tem_assinatura = bool(assinatura)

    return render_template('paginaUnica.html', username=username, user_id=user_id, tem_assinatura=tem_assinatura)

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

    user_id = session['user_id']
    assinatura = Assinatura.query.filter_by(user_id=user_id, status='authorized').first()
    if not assinatura:
        return jsonify({"error": "Acesso negado. Assinatura não encontrada ou inativa."}), 403

    try:
        data = request.json
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

@app.route('/registrar_assinatura_teste/<int:user_id>')
def registrar_assinatura_teste(user_id):
    from datetime import datetime, timedelta

    nova_assinatura = Assinatura(
        user_id=user_id,
        preapproval_id=f"teste-{user_id}-{datetime.now().timestamp()}",
        email=User.query.get(user_id).email,
        status='authorized',
        data_inicio=datetime.now().isoformat(),
        data_fim=(datetime.now() + timedelta(days=365)).isoformat(),
        plano="Assinatura de Teste"
    )
    db.session.add(nova_assinatura)
    db.session.commit()
    return f"Assinatura registrada com sucesso para o usuário {user_id}"


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
        print("📥 Dados recebidos:", data)

        if data.get("type") == "preapproval":
            preapproval_id = data.get("data", {}).get("id")
            print("🔍 Preapproval ID:", preapproval_id)

            # ----- SIMULAÇÃO LOCAL PARA TESTE -----
            if preapproval_id == "TESTE_LOCAL":
                assinatura_data = {
                    "payer_email": "teste@exemplo.com",
                    "status": "authorized",
                    "reason": "Plano Premium",
                    "auto_recurring": {
                        "start_date": "2025-04-08T00:00:00Z",
                        "end_date": "2026-04-08T00:00:00Z"
                    }
                }
            else:
                headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}"
                }
                url = f"https://api.mercadopago.com/preapproval/{preapproval_id}"
                response = requests.get(url, headers=headers)
                assinatura_data = response.json()
                print("📦 Dados da assinatura:", assinatura_data)

            email = assinatura_data.get("payer_email")
            print("📧 Email do pagador:", email)

            if not email:
                print("❌ Email não encontrado na assinatura.")
                return jsonify({"error": "Email não encontrado na assinatura."}), 400

            user = User.query.filter_by(email=email).first()
            print("👤 Usuário encontrado:", user)

            if user:
                assinatura_existente = Assinatura.query.filter_by(preapproval_id=preapproval_id).first()
                print("🧾 Assinatura já existe?", assinatura_existente)

                if not assinatura_existente:
                    nova_assinatura = Assinatura(
                        user_id=user.id,
                        preapproval_id=preapproval_id,
                        email=email,
                        status=assinatura_data.get("status"),
                        data_inicio=assinatura_data.get("auto_recurring", {}).get("start_date"),
                        data_fim=assinatura_data.get("auto_recurring", {}).get("end_date"),
                        plano=assinatura_data.get("reason")
                    )
                    db.session.add(nova_assinatura)
                    db.session.commit()
                    print(f"✅ Assinatura registrada: {preapproval_id}")
                else:
                    print("⚠️ Assinatura já existe, não será duplicada.")
            else:
                print("❌ Usuário não encontrado no banco.")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO no webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500
    



if __name__ == '__main__':
    app.run(debug=True)
