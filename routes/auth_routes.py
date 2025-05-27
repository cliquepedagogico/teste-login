from flask import Blueprint, render_template, request, redirect, url_for, session
from models.assinatura import (
    cadastrar_assinatura,
    login_usuario,
    buscar_email_por_id,
    verificar_assinatura_por_email
)

# Cria blueprint
auth = Blueprint('auth', __name__)

# ======== ROTAS DE AUTENTICAÇÃO ========

@auth.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        data_nascimento = request.form['data_nascimento']

        resultado = cadastrar_assinatura(username, email, password, telefone, cpf, data_nascimento)
        if resultado is not True:
            return resultado

        return redirect(url_for('auth.login'))

    return render_template('cadastrar.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form['username']
        password = request.form['password']

        user = login_usuario(user_input, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            session['status_assinatura'] = user.status
            return redirect(url_for('auth.index'))
        else:
            error = "Usuário, e-mail ou senha incorretos"

    return render_template('index.html', error=error)


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))


@auth.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')
    tem_assinatura = False

    if user_id:
        email = buscar_email_por_id(user_id)
        if email:
            tem_assinatura = verificar_assinatura_por_email(email)

    return render_template('paginaUnica.html', username=username, user_id=user_id, tem_assinatura=tem_assinatura)
