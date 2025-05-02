from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
import mercadopago
from db_assinatura import Assinatura 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import openai
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
    atualizar_assinatura_por_subscription_id
)

# Inicializa o Flask
app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Carrega variáveis do .env
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
YOUR_DOMAIN = "https://teste-login-0hdz.onrender.com"
# sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_TOKEN"))

# Banco de dados MySQL remoto para conversas
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Caminho do banco SQLite para assinatura
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'sistema_assinaturas.db')

agora = datetime.now()
fim = agora + timedelta(days=365)
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



@app.route('/criar-assinatura')
def criar_assinatura():
    if 'user_id' not in session:
        return "Usuário não logado."

    user_id = session['user_id']
    email = buscar_email_por_id(user_id)

    if not email:
        return "E-mail não encontrado para o usuário logado."

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1
            }],
            mode='subscription',
            success_url=f"{YOUR_DOMAIN}/?status=sucesso",
            cancel_url=f"{YOUR_DOMAIN}/?status=cancelado"
        )
        return redirect(checkout_session.url)
    except Exception as e:
        print("❌ Erro ao criar checkout com Stripe:", str(e))
        return "❌ Falha técnica ao criar assinatura"

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        print("❌ Assinatura inválida no webhook.")
        return "Assinatura inválida", 400
    except Exception as e:
        print("❌ Erro geral no webhook:", str(e))
        return "Erro", 400

    event_type = event.get('type')
    data_object = event['data']['object']

    if event_type == 'checkout.session.completed':
        subscription_id = data_object.get('subscription')
        customer_email = data_object.get('customer_email')

        if subscription_id and customer_email:
            atualizar_ou_criar_assinatura(customer_email, subscription_id, 'ativa')

    elif event_type == 'customer.subscription.deleted':
        subscription_id = data_object.get('id')
        if subscription_id:
            desativar_assinatura(subscription_id)

    return jsonify({'status': 'ok'}), 200

def buscar_email_por_id(user_id):
    session = Session()
    try:
        assinatura = session.query(Assinatura).filter_by(id=user_id).first()
        return assinatura.email if assinatura else None
    finally:
        session.close()

def atualizar_ou_criar_assinatura(email, subscription_id, status_assinatura):
    session = Session()
    try:
        assinatura = session.query(Assinatura).filter_by(email=email).first()
        if assinatura:
            assinatura.stripe_subscription_id = subscription_id
            assinatura.status = status_assinatura
            assinatura.data_inicio = datetime.now()
            session.commit()
            print(f"✅ Assinatura salva/atualizada para {email}")
        else:
            print(f"⚠️ E-mail {email} não encontrado para salvar assinatura.")
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao salvar assinatura: {str(e)}")
    finally:
        session.close()

@app.route('/cancelar-assinatura-direto')
def cancelar_assinatura_direto():
    if 'user_id' not in session:
        return "Usuário não logado."

    session_db = Session()
    try:
        user_id = session['user_id']
        assinatura = session_db.query(Assinatura).filter_by(id=user_id).first()

        if assinatura and assinatura.stripe_subscription_id:
            desativar_assinatura(assinatura.stripe_subscription_id)
            return redirect('/?status=assinatura_cancelada')
        else:
            return "Assinatura não encontrada para este usuário."
    except Exception as e:
        print(f"❌ Erro ao cancelar assinatura direto: {str(e)}")
        return "Erro interno ao cancelar assinatura"
    finally:
        session_db.close()


def desativar_assinatura(subscription_id):
    session = Session()
    try:
        assinatura = session.query(Assinatura).filter_by(stripe_subscription_id=subscription_id).first()
        if assinatura:
            assinatura.status = 'cancelada'
            assinatura.data_expiracao = datetime.now()
            session.commit()
            print(f"❌ Assinatura cancelada para {assinatura.email}")
        else:
            print(f"⚠️ Nenhuma assinatura encontrada com ID {subscription_id}")
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao cancelar assinatura: {str(e)}")
    finally:
        session.close()

# @app.route('/criar-assinatura')
# def criar_assinatura():
#     if 'user_id' not in session:
#         return "Usuário não logado."

#     user_id = session['user_id']
#     email = buscar_email_por_id(user_id)

#     if not email:
#         return "E-mail não encontrado para o usuário logado."

#     preference_data = {
#         "reason": "Assinatura mensal do Clique Pedagógico",
#         "auto_recurring": {
#             "frequency": 1,
#             "frequency_type": "months",
#             "transaction_amount": 5.5,
#             "currency_id": "BRL",
#             "start_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000-03:00"),
#             "end_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000-03:00")
#         },
#         "back_url": "https://9845-170-239-253-133.ngrok-free.app",
#         "payer_email": email
#     }

#     try:
#         preapproval_response = sdk.preapproval().create(preference_data)
#         if preapproval_response["status"] == 201:
#             init_point = preapproval_response["response"]["init_point"]
#             # 🔁 NÃO SALVA NADA AQUI
#             return redirect(init_point)
#         else:
#             print("❌ Erro ao criar assinatura:", preapproval_response)
#             return "❌ Erro ao criar assinatura"
#     except Exception as e:
#         print("❌ Exceção ao criar assinatura:", str(e))
#         return "❌ Falha técnica ao criar assinatura"

    
# def verificar_preapproval_existente(user_id):
#     session = Session()
#     try:
#         assinatura = session.query(Assinatura).filter_by(id=user_id).first()
#         return bool(assinatura and assinatura.stripe_subscription_id)
#     finally:
#         session.close()

# @app.route('/webhook', methods=['POST'])
# def mercado_pago_webhook():
#     content_type = request.headers.get('Content-Type', '')
#     if 'application/json' in content_type:
#         data = request.get_json()
#     elif 'application/x-www-form-urlencoded' in content_type:
#         data = request.form.to_dict()
#     else:
#         return 'Tipo de conteúdo não suportado', 415

#     print("📨 Webhook recebido:", data)

#     if data.get('type') == 'subscription_preapproval':
#         try:
#             preapproval_id = data['data']['id']
#             preapproval_info = sdk.preapproval().get(preapproval_id)

#             if preapproval_info['status'] == 200:
#                 assinatura = preapproval_info['response']
#                 print("🧾 Conteúdo completo da assinatura:", assinatura)

#                 status_assinatura = assinatura.get('status')
#                 subscription_id = assinatura.get('id')

#                 if subscription_id and status_assinatura:
#                     status_convertido = mapear_status(status_assinatura)
#                     atualizar_assinatura_por_subscription_id(subscription_id, status_convertido)
#                 else:
#                     print("⚠️ Dados incompletos. Assinatura não atualizada.")
#             else:
#                 print(f"❌ preapproval_id {preapproval_id} não retornou dados válidos.")

#         except Exception as e:
#             print("❌ Erro ao processar webhook do Mercado Pago:", str(e))

#     return jsonify({'status': 'ok'}), 200

# def buscar_email_por_id(user_id):
#     session = Session()
#     try:
#         assinatura = session.query(Assinatura).filter_by(id=user_id).first()
#         if assinatura:
#             return assinatura.email
#         else:
#             print(f"⚠️ Nenhum registro encontrado com ID {user_id}")
#             return None
#     finally:
#         session.close()

# def salvar_preapproval_id(user_id, preapproval_id):
#     session = Session()
#     try:
#         assinatura = session.query(Assinatura).filter_by(id=user_id).first()
#         if assinatura:
#             assinatura.stripe_subscription_id = preapproval_id  # sobrescreve normalmente
#             session.commit()
#             print(f"✅ preapproval_id atualizado para user_id {user_id}")
#         else:
#             print(f"❌ Usuário com ID {user_id} não encontrado.")
#     except Exception as e:
#         session.rollback()
#         print(f"❌ Erro ao salvar preapproval_id: {str(e)}")
#     finally:
#         session.close()

# def atualizar_assinatura_por_subscription_id(subscription_id, status_assinatura):
#     session = Session()
#     try:
#         assinatura = session.query(Assinatura).filter_by(stripe_subscription_id=subscription_id).first()
#         if assinatura:
#             assinatura.status = status_assinatura
#             assinatura.data_inicio = datetime.now()
#             session.commit()
#             print(f"🔁 Assinatura atualizada via webhook para {assinatura.email} (subscription_id={subscription_id})")
#         else:
#             print(f"⚠️ Nenhuma assinatura encontrada com subscription_id {subscription_id}")

#     except Exception as e:
#         session.rollback()
#         print(f"❌ Erro ao atualizar assinatura via webhook: {str(e)}")
#     finally:
#         session.close()

# def mapear_status(status_mercado_pago):
#     if status_mercado_pago == 'authorized':
#         return 'ativa'
#     elif status_mercado_pago == 'paused':
#         return 'pausada'
#     elif status_mercado_pago == 'cancelled':
#         return 'inativa'
#     else:
#         return 'inativa'

if __name__ == '__main__':
    app.run(debug=True)
