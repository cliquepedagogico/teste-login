from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'minha_chave_secreta'  # Necessário para sessões
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/jader/OneDrive/Área de Trabalho/login chat/instance/historico.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin, db.Model):  # Adicionado UserMixin para login
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('app', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username, password=password).first()
    
    if user:
        login_user(user)  # Faz login do usuário e cria a sessão
        session['user_id'] = user.id  # Guarda a sessão do usuário
        return jsonify({"success": True, "message": "Login bem-sucedido", "user_id": user.id})
    else:
        return jsonify({"success": False, "message": "Usuário ou senha incorretos"})
    

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)  # Remove a sessão do usuário
    return jsonify({"success": True, "message": "Logout realizado com sucesso"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5002)
