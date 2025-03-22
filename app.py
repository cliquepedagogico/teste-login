from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Caminho absoluto para evitar criação de instance/
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'historico.db')

# Verifica se o banco existe antes de iniciar
if not os.path.exists(DATABASE_PATH):
    raise FileNotFoundError(f'O banco de dados não foi encontrado em: {DATABASE_PATH}')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
db = SQLAlchemy(app)

# Modelo de Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('inicio'))
        else:
            error = 'Usuário ou senha incorretos'

    return render_template('index.html', error=error)

@app.route('/inicio')
def inicio():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('posLogin/inicio.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
