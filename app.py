from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import stripe
import openai
from datetime import datetime, timedelta

# Blueprints das rotas
from routes.auth_routes import auth
from routes.assinatura_routes import assinatura_bp
from routes.chat_routes import chat_bp

# Configuração do projeto
from config.config import Config

# Inicializa Flask
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Registra blueprints
app.register_blueprint(auth)
app.register_blueprint(assinatura_bp)
app.register_blueprint(chat_bp)

# Configura integrações externas
openai.api_key = Config.OPENAI_API_KEY
stripe.api_key = Config.STRIPE_SECRET_KEY

# Banco de dados principal (conversas)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Variáveis globais opcionais
STRIPE_WEBHOOK_SECRET = Config.STRIPE_WEBHOOK_SECRET
STRIPE_PRICE_ID = Config.STRIPE_PRICE_ID
LINK_PAGAMENTO = Config.LINK_PAGAMENTO
YOUR_DOMAIN = Config.YOUR_DOMAIN

# Apenas se precisar usar no futuro (ex.: relatórios)
agora = datetime.now()
fim = agora + timedelta(days=365)

if __name__ == '__main__':
    app.run(debug=True)
