from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()
DB_URI = os.getenv("DB_URI")  # <- Esse é o banco do chat

# Configura o engine e session
engine = create_engine(DB_URI, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Modelos
class Conversa(Base):
    __tablename__ = 'conversas'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class Mensagem(Base):
    __tablename__ = 'mensagens'
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id'))
    remetente = Column(String(50))
    mensagem = Column(Text)
    data_hora = Column(DateTime, default=datetime.utcnow)

# Cria as tabelas se não existirem
Base.metadata.create_all(engine)

# Funções
def registrar_conversa(user_id, titulo):
    session = Session()
    try:
        nova = Conversa(
            user_id=user_id,
            title=titulo,
            created_at=datetime.utcnow()
        )
        session.add(nova)
        session.commit()
        return nova.id
    except Exception as e:
        session.rollback()
        print(f"[ERRO] registrar_conversa: {str(e)}")
        return None
    finally:
        session.close()

def salvar_mensagem(conversa_id, remetente, mensagem):
    session = Session()
    try:
        nova = Mensagem(
            conversa_id=conversa_id,
            remetente=remetente,
            mensagem=mensagem,
            data_hora=datetime.utcnow()
        )
        session.add(nova)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERRO] salvar_mensagem: {str(e)}")
    finally:
        session.close()

def carregar_conversas_ordenadas(user_id):
    session = Session()
    try:
        conversas = session.query(Conversa)\
            .filter_by(user_id=user_id)\
            .order_by(Conversa.created_at.desc())\
            .all()
        return [(c.id, c.title, c.created_at) for c in conversas]
    except Exception as e:
        print(f"[ERRO] carregar_conversas_ordenadas: {str(e)}")
        return []
    finally:
        session.close()

def carregar_mensagem(conversa_id):
    session = Session()
    try:
        mensagens = session.query(Mensagem)\
            .filter_by(conversa_id=conversa_id)\
            .order_by(Mensagem.data_hora)\
            .all()
        return [{"remetente": m.remetente, "mensagem": m.mensagem, "data_hora": m.data_hora.strftime('%Y-%m-%d %H:%M:%S')} for m in mensagens]
    except Exception as e:
        print(f"[ERRO] carregar_mensagem: {str(e)}")
        return []
    finally:
        session.close()

def renomear_conversa(conversa_id, novo_titulo):
    session = Session()
    try:
        conversa = session.query(Conversa).filter_by(id=conversa_id).first()
        if conversa:
            conversa.title = novo_titulo
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERRO] renomear_conversa: {str(e)}")
    finally:
        session.close()

def excluir_conversa(conversa_id):
    session = Session()
    try:
        session.query(Mensagem).filter_by(conversa_id=conversa_id).delete()
        session.query(Conversa).filter_by(id=conversa_id).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[ERRO] excluir_conversa: {str(e)}")
    finally:
        session.close()
