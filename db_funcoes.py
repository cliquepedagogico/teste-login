from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, func, desc
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Configuração de conexão
DB_URI = "mysql+pymysql://u579582402_adminChatFlask:Xu0LFxW^3@cliquepedagogico.com.br/u579582402_HistoricoChat"

engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

# Modelos
class Conversa(Base):
    __tablename__ = 'conversas'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    mensagens = relationship("Mensagem", back_populates="conversa", cascade="all, delete-orphan")

class Mensagem(Base):
    __tablename__ = 'mensagens'
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id', ondelete="CASCADE"), nullable=False)
    remetente = Column(String(255))
    mensagem = Column(Text)
    data_hora = Column(TIMESTAMP, server_default=func.now())

    conversa = relationship("Conversa", back_populates="mensagens")

# 🧩 Funções

def registrar_conversa(user_id, title):
    nova_conversa = Conversa(user_id=user_id, title=title)
    session.add(nova_conversa)
    session.commit()
    return nova_conversa.id

def salvar_mensagem(conversa_id, remetente, mensagem):
    nova_mensagem = Mensagem(conversa_id=conversa_id, remetente=remetente, mensagem=mensagem)
    session.add(nova_mensagem)
    session.commit()
    print(f"Mensagem salva: {mensagem}")

def carregar_conversas(user_id):
    return session.query(Conversa.id, Conversa.title).filter_by(user_id=user_id).all()

def carregar_mensagem(conversa_id):
    mensagens = session.query(Mensagem.remetente, Mensagem.mensagem).filter_by(conversa_id=conversa_id).order_by(Mensagem.data_hora.asc()).all()
    return [{"remetente": r, "mensagem": m} for r, m in mensagens]

def renomear_conversa(conversa_id, novo_titulo):
    conversa = session.query(Conversa).filter_by(id=conversa_id).first()
    if conversa:
        conversa.title = novo_titulo
        session.commit()

def excluir_conversa(conversa_id):
    conversa = session.query(Conversa).filter_by(id=conversa_id).first()
    if conversa:
        session.delete(conversa)
        session.commit()

def carregar_conversas_ordenadas(user_id):
    try:
        subquery = (
            session.query(
                Mensagem.conversa_id,
                func.max(Mensagem.data_hora).label("ultima_modificacao")
            )
            .group_by(Mensagem.conversa_id)
            .subquery()
        )

        resultados = (
            session.query(Conversa.id, Conversa.title, subquery.c.ultima_modificacao)
            .join(subquery, subquery.c.conversa_id == Conversa.id)
            .filter(Conversa.user_id == user_id)
            .order_by(desc(subquery.c.ultima_modificacao))
            .all()
        )
        return resultados

    except Exception as e:
        session.rollback()
        print("❌ Erro em carregar_conversas_ordenadas:", e)
        return []

