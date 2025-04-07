from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Configuração do Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'usuarios.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy
db = SQLAlchemy(app)

# Modelo da Tabela Assinatura
class Assinatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    preapproval_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100))
    status = db.Column(db.String(50))  # Ex: "authorized", "paused", "cancelled"
    data_inicio = db.Column(db.String(50))
    data_fim = db.Column(db.String(50))
    plano = db.Column(db.String(100))

    def __repr__(self):
        return f'<Assinatura {self.email} - {self.status}>'

# Cria a tabela no banco de dados
with app.app_context():
    db.create_all()
    print("✅ Tabela 'Assinatura' criada com sucesso no banco usuarios.db.")
