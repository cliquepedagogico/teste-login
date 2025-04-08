from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    cpf = db.Column(db.String(14))
    data_nascimento = db.Column(db.String(20))

class Assinatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    preapproval_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50))
    data_inicio = db.Column(db.String(50))
    data_fim = db.Column(db.String(50))
    plano = db.Column(db.String(100))

    user = db.relationship('User', backref=db.backref('assinaturas', lazy=True))
