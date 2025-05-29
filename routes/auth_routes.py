from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from argon2 import PasswordHasher, exceptions
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
import re
from models.assinatura import Session, Assinatura
from models.assinatura import (
    cadastrar_assinatura,
    login_usuario,
    buscar_email_por_id,
    verificar_assinatura_por_email
)

auth = Blueprint('auth', __name__)
ph = PasswordHasher()

# Serializer configurado com a chave
def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

# Função para enviar e-mail de confirmação
def enviar_email_confirmacao(email, token):
    confirm_url = url_for('auth.confirmar_email', token=token, _external=True)
    assunto = 'Confirme seu cadastro'
    corpo = f'Olá! Clique no link para confirmar seu cadastro:\n\n{confirm_url}'

    msg = Message(assunto, recipients=[email])
    msg.body = corpo

    try:
        with current_app.app_context():
            mail = current_app.extensions['mail']
            mail.send(msg)
        print(f'✅ E-mail de confirmação enviado para {email}')
    except Exception as e:
        print(f'❌ Erro ao enviar e-mail: {str(e)}')

# ROTA: Cadastrar
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

        # Validações
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

        # 🔒 Gera hash da senha usando Argon2
        hashed_password = ph.hash(password)

        # Monta dados no token
        serializer = get_serializer()
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'telefone': telefone,
            'cpf': cpf,
            'data_nascimento': data_nascimento
        }
        token = serializer.dumps(user_data, salt='email-confirm')

        enviar_email_confirmacao(email, token)
        flash('Enviamos um e-mail para confirmação. Verifique sua caixa de entrada.', 'info')
        return redirect(url_for('auth.index'))

    return render_template('cadastrar.html')

# ROTA: Confirmar e-mail
@auth.route('/confirmar_email/<token>')
def confirmar_email(token):
    serializer = get_serializer()
    try:
        user_data = serializer.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        flash('O link expirou. Tente novamente.', 'danger')
        return redirect(url_for('auth.cadastrar'))
    except BadSignature:
        flash('Link inválido.', 'danger')
        return redirect(url_for('auth.cadastrar'))

    try:
        resultado = cadastrar_assinatura(
            user_data['username'],
            user_data['email'],
            user_data['password'],
            user_data['telefone'],
            user_data['cpf'],
            user_data['data_nascimento']
        )

        if resultado is True:
            flash('Cadastro confirmado com sucesso! Agora você pode fazer login.', 'success')
        else:
            # ⚠️ Aqui mostramos a mensagem exata retornada (email duplicado, CPF duplicado ou erro interno)
            flash(f'{resultado}', 'danger')

    except Exception as e:
        flash(f'Erro inesperado ao salvar no banco: {str(e)}', 'danger')
        print(f'❌ Erro inesperado ao salvar no banco: {str(e)}')

    return redirect(url_for('auth.login'))


# Senha forte
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

# ROTA: Login
from argon2 import PasswordHasher, exceptions

ph = PasswordHasher()

@auth.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form['username']
        password = request.form['password']

        user = login_usuario(user_input)  # sem passar senha aqui!

        if user:
            try:
                ph.verify(user.senha, password)

                session['user_id'] = user.id
                session['username'] = user.username
                session['email'] = user.email
                session['status_assinatura'] = user.status

                return redirect(url_for('auth.index'))

            except exceptions.VerifyMismatchError:
                error = "Senha incorreta"
        else:
            error = "Usuário ou e-mail não encontrado"

    return render_template('index.html', error=error)

# ROTA: Logout
@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))

# ROTA: Página principal
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


@auth.route('/pagina_usuario', methods=['GET'])
def pagina_usuario():
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar essa página.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db_session = Session()

    try:
        usuario = db_session.query(Assinatura).filter_by(id=user_id).first()

        if not usuario:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('auth.index'))

        return render_template(
            'pagina_usuario.html',
            usuario=usuario
        )

    except Exception as e:
        flash(f'Erro ao carregar os dados do usuário: {str(e)}', 'danger')
        print(f'❌ Erro ao buscar usuário no banco: {str(e)}')
        return redirect(url_for('auth.index'))

    finally:
        db_session.close()
