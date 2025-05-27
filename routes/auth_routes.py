from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from datetime import datetime
import re
from flask_mail import Message
from flask import current_app
from models.assinatura import (
    cadastrar_assinatura,
    login_usuario,
    buscar_email_por_id,
    verificar_assinatura_por_email
)

auth = Blueprint('auth', __name__)

# Serializer configurado com a chave do app
def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

# Função para enviar e-mail de confirmação
# Função para enviar e-mail de confirmação
def enviar_email_confirmacao(email, token):
    confirm_url = url_for('auth.confirmar_email', token=token, _external=True)
    assunto = 'Confirme seu cadastro'
    corpo = f'Olá! Clique no link para confirmar seu cadastro: {confirm_url}'

    msg = Message(assunto, recipients=[email])
    msg.body = corpo

    try:
        with current_app.app_context():
            mail = current_app.extensions['mail']
            mail.send(msg)
        print(f'✅ E-mail de confirmação enviado para {email}')
    except Exception as e:
        print(f'❌ Erro ao enviar e-mail: {str(e)}')
# ======== ROTAS DE AUTENTICAÇÃO ========

@auth.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        data_nascimento_raw = request.form['data_nascimento']

        try:
            ano, mes, dia = data_nascimento_raw.split('-')
            data_nascimento = f"{dia}/{mes}/{ano}"
        except Exception:
            flash('Formato de data inválido.', 'danger')
            return redirect(url_for('auth.cadastrar'))

        # Regex
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        telefone_pattern = r'^\(\d{2}\)\s\d{5}-\d{4}$'
        cpf_pattern = r'^\d{3}\.\d{3}\.\d{3}-\d{2}$'
        data_pattern = r'^\d{2}/\d{2}/\d{4}$'

        if not re.match(email_pattern, email):
            flash('Formato de e-mail inválido.', 'danger')
            return redirect(url_for('auth.cadastrar'))

        if not re.match(telefone_pattern, telefone):
            flash('Formato de telefone inválido.', 'danger')
            return redirect(url_for('auth.cadastrar'))

        if not re.match(cpf_pattern, cpf):
            flash('Formato de CPF inválido.', 'danger')
            return redirect(url_for('auth.cadastrar'))

        if not re.match(data_pattern, data_nascimento):
            flash('Formato de data inválido.', 'danger')
            return redirect(url_for('auth.cadastrar'))

        if check_password_strength(password) == 'fraca':
            flash('A senha é muito fraca.', 'danger')
            return redirect(url_for('auth.cadastrar'))

        # Gera token e armazena dados no session
        serializer = get_serializer()
        token = serializer.dumps(email, salt='email-confirm')

        session['pending_user'] = {
            'username': username,
            'email': email,
            'password': password,
            'telefone': telefone,
            'cpf': cpf,
            'data_nascimento': data_nascimento
        }

        enviar_email_confirmacao(email, token)
        flash('Enviamos um e-mail para confirmação. Verifique sua caixa de entrada.', 'info')
        return redirect(url_for('auth.index'))

    return render_template('cadastrar.html')

@auth.route('/confirmar_email/<token>')
def confirmar_email(token):
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        flash('O link expirou. Tente novamente.', 'danger')
        return redirect(url_for('auth.cadastrar'))
    except BadSignature:
        flash('Link inválido.', 'danger')
        return redirect(url_for('auth.cadastrar'))

    pending_user = session.get('pending_user')
    if pending_user and pending_user['email'] == email:
        resultado = cadastrar_assinatura(
            pending_user['username'],
            pending_user['email'],
            pending_user['password'],
            pending_user['telefone'],
            pending_user['cpf'],
            pending_user['data_nascimento']
        )
        if resultado is True:
            flash('Cadastro confirmado com sucesso! Agora você pode fazer login.', 'success')
        else:
            flash('Erro ao salvar o usuário no banco.', 'danger')

        session.pop('pending_user', None)
    else:
        flash('Nenhum cadastro pendente encontrado ou já confirmado.', 'warning')

    return redirect(url_for('auth.login'))

# Validação de senha forte
def check_password_strength(password):
    if len(password) < 8:
        return 'fraca'
    if not re.search(r'[A-Z]', password):
        return 'fraca'
    if not re.search(r'[a-z]', password):
        return 'fraca'
    if not re.search(r'[0-9]', password):
        return 'fraca'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return 'fraca'
    return 'forte'

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
