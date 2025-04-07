from app import app, db

# Envolve o comando dentro do contexto da aplicação
with app.app_context():
    db.create_all()
    print("✅ Banco de dados 'usuarios.db' recriado com sucesso!")
