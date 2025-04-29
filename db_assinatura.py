from sqlalchemy import create_engine, Column, Integer, String, DateTime, or_
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
ASS = os.getenv("ASSINATURA_DB_URI")
engine = create_engine(ASS, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Assinatura(Base):
    __tablename__ = 'assinatura'
    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    email = Column(String(100), unique=True)
    senha = Column(String(100))
    telefone = Column(String(20))
    cpf = Column(String(20), unique=True)
    data_nascimento = Column(String(20))
    stripe_subscription_id = Column(String(255))
    status = Column(String(20), default='inativa')
    data_inicio = Column(DateTime)
    data_expiracao = Column(DateTime)

Base.metadata.create_all(engine)

def verificar_assinatura_por_email(email):
    session = Session()
    assinatura = session.query(Assinatura).filter_by(email=email).order_by(Assinatura.data_inicio.desc()).first()
    session.close()
    return assinatura and assinatura.status == 'ativa'

def cadastrar_assinatura(username, email, senha, telefone, cpf, data_nascimento):
    session = Session()
    existente_email = session.query(Assinatura).filter(Assinatura.email == email).first()
    if existente_email:
        session.close()
        return "⚠️ Este e-mail já está cadastrado."

    existente_cpf = session.query(Assinatura).filter(Assinatura.cpf == cpf).first()
    if existente_cpf:
        session.close()
        return "⚠️ Este CPF já está cadastrado."

    nova = Assinatura(
        username=username,
        email=email,
        senha=senha,
        telefone=telefone,
        cpf=cpf,
        data_nascimento=data_nascimento
    )
    session.add(nova)
    session.commit()
    session.close()
    return True

def login_usuario(user_input, senha):
    session = Session()
    user = session.query(Assinatura).filter(
        or_(Assinatura.username == user_input, Assinatura.email == user_input),
        Assinatura.senha == senha
    ).first()
    session.close()
    return user

def buscar_email_por_id(user_id):
    session = Session()
    usuario = session.query(Assinatura).filter_by(id=user_id).first()
    session.close()
    return usuario.email if usuario else None

def cancelar_assinatura_por_email(email):
    session = Session()
    assinatura = session.query(Assinatura).filter_by(email=email).first()
    if assinatura:
        assinatura.status = 'cancelada'
        assinatura.data_expiracao = datetime.now()
        session.commit()
    session.close()

def atualizar_ou_criar_assinatura(email, subscription_id, status_assinatura):
    session = Session()
    assinatura = session.query(Assinatura).filter_by(email=email).first()
    if assinatura:
        assinatura.stripe_subscription_id = subscription_id  # usando o mesmo campo para MP
        assinatura.status = status_assinatura
        assinatura.data_inicio = datetime.now()
    else:
        assinatura = Assinatura(
            email=email,
            stripe_subscription_id=subscription_id,
            status=status_assinatura,
            data_inicio=datetime.now()
        )
        session.add(assinatura)
    session.commit()
    session.close()
