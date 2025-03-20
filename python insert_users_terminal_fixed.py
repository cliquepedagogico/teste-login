from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import app, db, User  # Importa o app para fornecer contexto

# Função para adicionar usuários pelo terminal
def add_user():
    username = input("Digite o nome de usuário: ")
    password = input("Digite a senha: ")

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    print("Usuário cadastrado com sucesso!")

if __name__ == "__main__":
    with app.app_context():  # Garante que a operação ocorra dentro do contexto do Flask
        add_user()
