# (Cabeçalho permanece o mesmo)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
import openai
import requests
import sqlite3
from dotenv import load_dotenv
from datetime import datetime
import mercadopago
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Carrega .env
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
ACCESS_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")

# Caminho do banco de dados principal
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'sistema_assinaturas.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Funções externas
try:
    from db import (
        registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas,
        carregar_mensagem, renomear_conversa, excluir_conversa
    )
except ImportError as e:
    print(f"Erro ao importar funções de 'db.py': {e}")
    registrar_conversa = salvar_mensagem = carregar_conversas_ordenadas = carregar_mensagem = renomear_conversa = excluir_conversa = None

# Verificação de assinatura
def verificar_assinatura_por_email(email):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status FROM assinatura
        WHERE email = ?
        ORDER BY data_inicio DESC
        LIMIT 1
    """, (email,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado and resultado[0] == 'authorized'

# Cadastro
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        data_nascimento = request.form['data_nascimento']

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM assinatura WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return "⚠️ Este e-mail já está cadastrado."

        cursor.execute("""
            INSERT INTO assinatura (username, email, senha, telefone, cpf, data_nascimento)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, password, telefone, cpf, data_nascimento))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('cadastrar.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, senha, status
            FROM assinatura
            WHERE (username = ? OR email = ?) AND senha = ?
        """, (user_input, user_input, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]
            session['status_assinatura'] = user[4]
            return redirect('/')
        else:
            error = "Usuário, e-mail ou senha incorretos"

    return render_template('index.html', error=error)

# Página inicial
@app.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')
    tem_assinatura = False

    if user_id:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM assinatura WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            email = result[0]
            tem_assinatura = verificar_assinatura_por_email(email)

    return render_template('paginaUnica.html', username=username, user_id=user_id, tem_assinatura=tem_assinatura)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Geração de imagem com OpenAI
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

# Chat com imagem ou texto
@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    user_id = session['user_id']
    try:
        data = request.json
        user_message = data.get('message')
        funcionalidade = data.get('funcionalidade')
        conversa_id = data.get('conversa_id')
        history = data.get('history', [])

        if not conversa_id:
            title = user_message[:20]
            conversa_id = registrar_conversa(user_id, title) if registrar_conversa else None

        if salvar_mensagem:
            salvar_mensagem(conversa_id, 'user', user_message)

        if funcionalidade == 'gerar_imagem':
            url_imagem = gerar_imagem(user_message)
            if salvar_mensagem:
                salvar_mensagem(conversa_id, 'vix', url_imagem)
            if "Erro" in url_imagem:
                return jsonify({"response": url_imagem})
            return jsonify({"image_url": url_imagem, "conversa_id": conversa_id})

        messages = [{"role": "system", "content": "Aqui vai sua instrução do sistema"}] + history + [{"role": "user", "content": user_message}]
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

# Resto das rotas continua igual
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
    
@app.route('/carregar_conversas', methods=['POST'])
def carregar_conversas_usuario():
    if not carregar_conversas_ordenadas:
        return jsonify({"error": "Erro ao carregar conversas"}), 500
    user_id = session.get('user_id')
    conversas = carregar_conversas_ordenadas(user_id)
    return jsonify([{"id": conv[0], "title": conv[1]} for conv in conversas])
# (carregar_conversas_usuario, carregar_mensagem_view, renomear, excluir_conversa_view, carregar_historico etc.)

@app.route('/criar-assinatura', methods=['POST'])
def criar_assinatura():
    if 'email' not in session:
        return "Você precisa estar logado para assinar."

    url = "https://api.mercadopago.com/preapproval"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    agora = datetime.now()
    fim = agora + timedelta(days=365)

    body = {
        "reason": "Assinatura mensal Clique Pedagógico",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": 0.5,  # valor simbólico
            "currency_id": "BRL",
            "start_date": agora.strftime("%Y-%m-%dT%H:%M:%S.000-03:00"),
            "end_date": fim.strftime("%Y-%m-%dT%H:%M:%S.000-03:00"),
            "repetitions": 12
        },
        "back_url": "https://SEU_DOMINIO.com.br/assinatura-concluida",  # ngrok ou render
        "payer_email": session.get("email"),
        "notification_url": "https://SEU_DOMINIO.com.br/webhook-mercado-pago"  # importante
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 201:
        assinatura = response.json()
        return redirect(assinatura["init_point"])
    else:
        print("🔴 Erro na requisição:", response.text)
        return f"Erro: {response.text}", 400

    
@app.route('/webhook-mercado-pago', methods=['POST'])
def webhook_mercado_pago():
    try:
        data = request.get_json()
        print("📨 Webhook recebido:", data)

        if not data or "type" not in data:
            return jsonify({"message": "Ignorado"}), 200

        if data["type"] == "subscription_preapproval":
            preapproval_id = data["data"]["id"]

            # Buscar detalhes da assinatura com a API
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }

            response = requests.get(f"https://api.mercadopago.com/preapproval/{preapproval_id}", headers=headers)
            assinatura = response.json()

            email = assinatura.get("payer_email")
            status = assinatura.get("status")
            data_inicio = assinatura.get("date_created")

            # Salvar ou atualizar no banco
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO assinatura (email, status, mercado_pago_id, data_inicio)
                VALUES (?, ?, ?, ?)
            """, (email, status, preapproval_id, data_inicio))

            conn.commit()
            conn.close()

            print(f"✅ Assinatura de {email} atualizada para status: {status}")

        return jsonify({"message": "OK"}), 200

    except Exception as e:
        print("❌ Erro no webhook:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/assinatura-concluida')
def assinatura_concluida():
    return "Assinatura criada com sucesso!"


if __name__ == '__main__':
    app.run(debug=True)
