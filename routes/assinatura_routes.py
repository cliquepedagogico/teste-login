from flask import Blueprint, request, jsonify, redirect, session
from config.config import Config
from models.assinatura import Assinatura, Session
from datetime import datetime
import stripe

# Cria blueprint
assinatura_bp = Blueprint('assinatura', __name__)

# Configura Stripe
STRIPE_WEBHOOK_SECRET = Config.STRIPE_WEBHOOK_SECRET
STRIPE_PRICE_ID = Config.STRIPE_PRICE_ID
YOUR_DOMAIN = Config.YOUR_DOMAIN
stripe.api_key = Config.STRIPE_SECRET_KEY


# ======== ROTAS DE ASSINATURA ========

@assinatura_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Assinatura inválida: {str(e)}")
        return 'Assinatura inválida', 400
    except Exception as e:
        print(f"❌ Erro geral no webhook: {str(e)}")
        return 'Erro no webhook', 400

    event_type = event.get('type')
    print(f"📨 Evento recebido: {event_type}")

    try:
        if event_type == 'invoice.paid':
            invoice = event['data']['object']
            subscription_id = invoice.get('subscription')

            if not subscription_id and invoice.get('lines', {}).get('data'):
                subscription_id = (
                    invoice['lines']['data'][0]
                    .get('parent', {})
                    .get('subscription_item_details', {})
                    .get('subscription')
                )

            if not subscription_id:
                print("⚠️ subscription_id ausente mesmo após fallback.")
                return jsonify({'status': 'erro'}), 400

            email = invoice.get('customer_email')

            print(f"💰 Fatura paga - Email: {email} | Subscription ID: {subscription_id}")

            if email:
                atualizar_ou_criar_assinatura(email, subscription_id, 'ativa')
            else:
                print("⚠️ E-mail ausente na fatura.")
                return jsonify({'status': 'erro'}), 400

        elif event_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')

            print(f"❌ Assinatura cancelada - Subscription ID: {subscription_id}")
            if subscription_id:
                desativar_assinatura(subscription_id)

        else:
            print(f"⚠️ Evento {event_type} recebido, mas não tratado.")

    except Exception as e:
        print(f"❌ Erro interno ao processar evento {event_type}: {str(e)}")
        return 'Erro interno no processamento', 500

    return jsonify({'status': 'ok'}), 200


@assinatura_bp.route('/cancelar-assinatura', methods=['GET'])
def cancelar_assinatura():
    if 'user_id' not in session:
        return "Usuário não logado", 401

    user_id = session['user_id']

    session_db = Session()
    try:
        assinatura = session_db.query(Assinatura).filter_by(id=user_id).first()
        if not assinatura or not assinatura.stripe_subscription_id:
            return "Assinatura não encontrada.", 404

        stripe.Subscription.modify(
            assinatura.stripe_subscription_id,
            cancel_at_period_end=True
        )

        assinatura.status = 'cancelada'
        assinatura.data_expiracao = datetime.now()
        session_db.commit()

        return "Assinatura será cancelada ao final do período atual."
    except Exception as e:
        session_db.rollback()
        print(f"Erro ao cancelar assinatura no Stripe: {str(e)}")
        return "Erro ao cancelar assinatura.", 500
    finally:
        session_db.close()


@assinatura_bp.route('/assinar')
def assinar():
    if 'user_id' not in session:
        return "Usuário não logado."

    user_id = session['user_id']
    email = buscar_email_por_id(user_id)

    if not email:
        return "E-mail não encontrado para o usuário logado."

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card", "boleto"],
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


# ======== FUNÇÕES AUXILIARES ========

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
            print(f"🔄 Atualizando assinatura para {email}")
            assinatura.stripe_subscription_id = subscription_id
            assinatura.status = status_assinatura
            assinatura.data_inicio = datetime.now()
            session.commit()
            print(f"✅ Assinatura atualizada com sucesso: {email}")
        else:
            print(f"⚠️ Nenhum registro encontrado para o e-mail: {email}")

    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao atualizar assinatura no banco: {str(e)}")
    finally:
        session.close()


def desativar_assinatura(subscription_id):
    session = Session()
    try:
        assinatura = session.query(Assinatura).filter_by(stripe_subscription_id=subscription_id).first()
        if assinatura:
            assinatura.status = 'cancelada'
            assinatura.data_expiracao = datetime.now()
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao desativar assinatura: {str(e)}")
    finally:
        session.close()
