from app import app
from models import db, User

with app.app_context():
    if not User.query.filter_by(email="teste@exemplo.com").first():
        novo_user = User(
            username="teste",
            email="teste@exemplo.com",
            password="123",
            telefone="00000000000",
            cpf="00000000000",
            data_nascimento="2000-01-01"
        )
        db.session.add(novo_user)
        db.session.commit()
        print("✅ Usuário teste criado!")
