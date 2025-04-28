from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
import openai
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timedelta
from db_funcoes import Conversa, registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas, carregar_mensagem, renomear_conversa, excluir_conversa
from db_assinatura import (
    Session,
    verificar_assinatura_por_email,
    cadastrar_assinatura,
    login_usuario,
    buscar_email_por_id,
    cancelar_assinatura_por_email,
    atualizar_ou_criar_assinatura
)

# Inicializa o Flask
app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Carrega variáveis do .env
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Banco de dados MySQL remoto para conversas
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Caminho do banco SQLite para assinatura
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'sistema_assinaturas.db')

# ======== ROTAS DO SISTEMA DE ASSINATURA ========

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        data_nascimento = request.form['data_nascimento']

        resultado = cadastrar_assinatura(username, email, password, telefone, cpf, data_nascimento)
        if resultado is not True:
            return resultado

        return redirect('/login')

    return render_template('cadastrar.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form['username']
        password = request.form['password']

        user = login_usuario(user_input, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            session['status_assinatura'] = user.status
            return redirect('/')
        else:
            error = "Usuário, e-mail ou senha incorretos"

    return render_template('index.html', error=error)

@app.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')
    tem_assinatura = False

    if user_id:
        email = buscar_email_por_id(user_id)
        if email:
            tem_assinatura = verificar_assinatura_por_email(email)

    return render_template('paginaUnica.html', username=username, user_id=user_id, tem_assinatura=tem_assinatura)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ======== ROTAS DO SISTEMA DE CONVERSAS (CHAT) ========

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
    try:
        data = request.json
        user_message = data.get('message')
        funcionalidade = data.get('funcionalidade')
        conversa_id = data.get('conversa_id')
        history = data.get('history', [])

        if not conversa_id:
            title = user_message[:20]
            conversa_id = registrar_conversa(user_id, title)

        salvar_mensagem(conversa_id, 'user', user_message)

        if funcionalidade == 'gerar_imagem':
            url_imagem = gerar_imagem(user_message)
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

@app.route('/excluir_conversa', methods=['POST'])
def excluir_conversa_view():
    try:
        excluir_conversa(request.json.get('conversa_id'))
        return jsonify({"status": "Conversa excluída"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ======== ASSINATURA - Stripe ========

# @app.route('/create-checkout-session', methods=['POST'])
# def create_checkout_session():
#     if 'email' not in session:
#         return jsonify({'error': 'Você precisa estar logado para assinar.'}), 403

#     try:
#         session_stripe = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             mode='subscription',
#             line_items=[{
#                 'price': os.getenv('STRIPE_PRICE_ID'),
#                 'quantity': 1
#             }],
#             customer_email=session['email'],
#             success_url='https://teste-login-0hdz.onrender.com',
#             cancel_url='https://teste-login-0hdz.onrender.com/cancelado',
#         )
#         return jsonify({'url': session_stripe.url})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 400

@app.route('/cancelar-assinatura', methods=['POST'])
def cancelar_assinatura():
    if 'email' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 403

    try:
        stripe.Subscription.delete(session.get("stripe_subscription_id", ""))
        cancelar_assinatura_por_email(session['email'])
        return jsonify({'message': 'Assinatura cancelada com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# @app.route('/webhook', methods=['POST'])
# def stripe_webhook():
#     payload = request.data
#     sig_header = request.headers.get('Stripe-Signature')
#     webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#     except stripe.error.SignatureVerificationError:
#         return 'Assinatura inválida', 400

#     if event['type'] == 'checkout.session.completed':
#         session_data = event['data']['object']
#         subscription_id = session_data.get('subscription')
#         customer_id = session_data.get('customer')
#         try:
#             email = stripe.Customer.retrieve(customer_id).get('email')
#             atualizar_ou_criar_assinatura(email, subscription_id)
#         except Exception as e:
#             print("Erro ao registrar assinatura:", str(e))

#     return jsonify({'status': 'ok'}), 200

# # ======== EXECUÇÃO ========

if __name__ == '__main__':
    app.run(debug=True)
