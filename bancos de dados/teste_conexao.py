import pymysql

# Dados de conexão (coloque sua senha abaixo)
config = {
    "host": "cliquepedagogico.com.br",
    "user": "u579582402_adminChatFlask",
    "password": "Xu0LFxW^3",
    "database": "u579582402_HistoricoChat",
    "port": 3306,
}

try:
    conexao = pymysql.connect(**config)
    print("✅ Conectado ao banco de dados com sucesso!")
    conexao.close()
except pymysql.MySQLError as e:
    print("❌ Erro ao conectar no banco de dados:")
    print(e)
