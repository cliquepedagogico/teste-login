# (Cabeçalho permanece o mesmo)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
import openai
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import mercadopago
import sqlite3
from db_funcoes import registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas, carregar_mensagem, renomear_conversa, excluir_conversa

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Carrega .env
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Banco de dados MySQL remoto (Hostinger)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Caminho do banco SQLite original (usado ainda para assinatura/login)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'sistema_assinaturas.db')

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
    return resultado and resultado[0] == 'ativa'

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

@app.route('/carregar_historico', methods=['POST'])
def carregar_historico():
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID não fornecido"}), 400

        conversas = carregar_conversas_ordenadas(user_id)
        historico = []

        for conv in conversas:
            conv_id = conv[0]
            title = conv[1]
            mensagens = carregar_mensagem(conv_id)

            historico.append({
                "conversa_id": conv_id,
                "title": title,
                "created_at": str(conv[2]) if len(conv) > 2 else None,
                "mensagens": mensagens
            })

        return jsonify(historico)

    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

@app.route('/excluir_conversa', methods=['POST'])
def excluir_conversa_view():
    try:
        conversa_id = request.json.get('conversa_id')
        excluir_conversa(conversa_id)
        return jsonify({"status": "Conversa excluída"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/carregar_mensagem', methods=['POST'])
def carregar_mensagem_view():
    try:
        conversa_id = request.json.get('conversa_id')
        historico = carregar_mensagem(conversa_id)
        return jsonify(historico)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/carregar_conversas', methods=['POST'])
def carregar_conversas_usuario():
    user_id = session.get('user_id')
    conversas = carregar_conversas_ordenadas(user_id)
    return jsonify([{"id": conv[0], "title": conv[1]} for conv in conversas])

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'email' not in session:
        return jsonify({'error': 'Você precisa estar logado para assinar.'}), 403

    try:
        session_stripe = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': os.getenv('STRIPE_PRICE_ID'),
                'quantity': 1
            }],
            customer_email=session['email'],
            success_url='https://teste-login-0hdz.onrender.com',
            cancel_url='https://teste-login-0hdz.onrender.com/cancelado',
        )
        return jsonify({'url': session_stripe.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/cancelar-assinatura', methods=['POST'])
def cancelar_assinatura():
    if 'email' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 403

    conn = sqlite3.connect('sistema_assinaturas.db')
    cursor = conn.cursor()

    cursor.execute("SELECT stripe_subscription_id FROM assinatura WHERE email = ?", (session['email'],))
    resultado = cursor.fetchone()
    conn.close()

    if not resultado:
        return jsonify({'error': 'Assinatura não encontrada'}), 404

    subscription_id = resultado[0]

    try:
        stripe.Subscription.delete(subscription_id)

        conn = sqlite3.connect('sistema_assinaturas.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE assinatura SET status = 'cancelada', data_expiracao = datetime('now') WHERE stripe_subscription_id = ?", (subscription_id,))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Assinatura cancelada com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        print("❌ Webhook com assinatura inválida")
        return 'Assinatura inválida', 400

    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        subscription_id = session_data.get('subscription')
        customer_id = session_data.get('customer')

        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get('email')

            conn = sqlite3.connect("sistema_assinaturas.db")
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM assinatura WHERE email = ?", (email,))
            usuario = cursor.fetchone()

            if usuario:
                cursor.execute("""
                    UPDATE assinatura
                    SET stripe_subscription_id = ?, status = ?, data_inicio = datetime('now')
                    WHERE email = ?
                """, (subscription_id, 'ativa', email))
            else:
                cursor.execute("""
                    INSERT INTO assinatura (email, stripe_subscription_id, status, data_inicio)
                    VALUES (?, ?, ?, datetime('now'))
                """, (email, subscription_id, 'ativa'))

            conn.commit()
            conn.close()
            print("✅ Assinatura salva com sucesso")

        except Exception as e:
            print("❌ Erro ao registrar assinatura:", str(e))

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True)
