from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import pymysql

# Conexão com o banco de dados MySQL (ajuste com sua senha)
DB_URI = "mysql+pymysql://u579582402_adminChatFlask:Xu0LFxW^3@cliquepedagogico.com.br/u579582402_HistoricoChat"

engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

# Tabela de Conversas
class Conversa(Base):
    __tablename__ = 'conversas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    mensagens = relationship("Mensagem", back_populates="conversa", cascade="all, delete-orphan")

# Tabela de Mensagens
class Mensagem(Base):
    __tablename__ = 'mensagens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id', ondelete="CASCADE"), nullable=False)
    remetente = Column(String(255))
    mensagem = Column(Text)
    data_hora = Column(TIMESTAMP, server_default=func.now())

    conversa = relationship("Conversa", back_populates="mensagens")

# Cria as tabelas no banco
Base.metadata.create_all(engine)

print("✅ Tabelas criadas com sucesso no banco MySQL!")
