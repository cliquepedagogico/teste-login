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
    senha = Column(String(255))
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
    try:
        # Verifica se e-mail já existe
        existente_email = session.query(Assinatura).filter(Assinatura.email == email).first()
        if existente_email:
            return "⚠️ Este e-mail já está cadastrado."

        # Verifica se CPF já existe
        existente_cpf = session.query(Assinatura).filter(Assinatura.cpf == cpf).first()
        if existente_cpf:
            return "⚠️ Este CPF já está cadastrado."

        # Cria nova assinatura
        nova = Assinatura(
            username=username,
            email=email.lower(),
            senha=senha,
            telefone=telefone,
            cpf=cpf,
            data_nascimento=data_nascimento,
            status='inativa'  # você pode ajustar o status inicial
        )
        session.add(nova)
        session.commit()
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao salvar assinatura: {str(e)}")
        return f"Erro ao salvar no banco: {str(e)}"

    finally:
        session.close()


def login_usuario(user_input):
    session = Session()
    user = session.query(Assinatura).filter(
        or_(Assinatura.username == user_input, Assinatura.email == user_input)
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
 
# ✅ NOVA FUNÇÃO: salvar preapproval_id na linha do usuário
def salvar_preapproval_id(user_id, preapproval_id):
    session = Session()
    try:
        assinatura = session.query(Assinatura).filter_by(id=user_id).first()
        if assinatura:
            assinatura.stripe_subscription_id = preapproval_id
            session.commit()
            print(f"✅ preapproval_id salvo com sucesso para o user_id {user_id}")
        else:
            print(f"❌ Usuário com ID {user_id} não encontrado para salvar o preapproval_id.")
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao salvar preapproval_id: {str(e)}")
    finally:
        session.close()

# ✅ NOVA FUNÇÃO: atualizar a assinatura via subscription_id (webhook)
def atualizar_assinatura_por_subscription_id(subscription_id, status_assinatura):
    session = Session()
    try:
        assinatura = session.query(Assinatura).filter_by(stripe_subscription_id=subscription_id).first()
        if assinatura:
            assinatura.status = status_assinatura
            assinatura.data_inicio = datetime.now()
            session.commit()
            print(f"🔁 Assinatura atualizada via webhook para {assinatura.email} (subscription_id={subscription_id})")
        else:
            print(f"⚠️ Nenhuma assinatura encontrada com subscription_id {subscription_id}")

    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao atualizar assinatura via webhook: {str(e)}")
    finally:
        session.close()