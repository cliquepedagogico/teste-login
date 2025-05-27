import os
from dotenv import load_dotenv

# Carrega o arquivo .env
load_dotenv()

class Config:
    # Chave secreta do Flask (você pode setar no .env também)
    SECRET_KEY = os.getenv('SECRET_KEY')

    # API OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Banco de dados principal (chat)
    DB_URI = os.getenv('DB_URI')

    # Banco de dados de assinaturas (se separado)
    ASSINATURA_DB_URI = os.getenv('ASSINATURA_DB_URI')

    # Stripe
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')
    LINK_PAGAMENTO = os.getenv('LINK_PAGAMENTO')
    YOUR_DOMAIN = os.getenv('YOUR_DOMAIN')

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')