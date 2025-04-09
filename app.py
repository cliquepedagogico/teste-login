from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import openai
import sqlite3
from dotenv import load_dotenv
from datetime import datetime
from models import db, User, Assinatura
import mercadopago

# Inicia o app
app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Carrega .env
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_TOKEN"))

# Caminho do banco de dados
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'usuarios.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Importa funções do db.py
try:
    from db import (
        registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas,
        carregar_mensagem, renomear_conversa, excluir_conversa
    )
except ImportError as e:
    print(f"Erro ao importar funções de 'db.py': {e}")
    registrar_conversa = salvar_mensagem = carregar_conversas_ordenadas = carregar_mensagem = renomear_conversa = excluir_conversa = None


def verificar_assinatura_por_email(email):
    conn = sqlite3.connect("assinaturas.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status FROM assinaturas
        WHERE email = ?
        ORDER BY data_criacao DESC
        LIMIT 1
    """, (email,))
    resultado = cursor.fetchone()
    conn.close()

    if resultado and resultado[0] == 'authorized':
        return True
    return False


# Função de cadastro
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        telefone = request.form['telefone']
        cpf = request.form['cpf']
        data_nascimento = request.form['data_nascimento']

        # Salvar no banco de dados SQLite
        conn = sqlite3.connect("assinaturas.db")
        cursor = conn.cursor()

        # Verifica se o e-mail já está cadastrado
        cursor.execute("SELECT * FROM assinaturas WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return "⚠️ Este e-mail já está cadastrado."

        cursor.execute("""
            INSERT INTO assinaturas (username, email, senha, telefone, cpf, data_nascimento)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, password, telefone, cpf, data_nascimento))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('cadastrar.html')


# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        user_input = request.form['username']  # pode ser username ou email
        password = request.form['password']

        import sqlite3
        conn = sqlite3.connect("assinaturas.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, senha, status
            FROM assinaturas
            WHERE (username = ? OR email = ?) AND senha = ?
        """, (user_input, user_input, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]
            session['status_assinatura'] = user[4]  # 'authorized' ou 'nao_assinante'
            return redirect('/')
        else:
            error = "Usuário, e-mail ou senha incorretos"

    return render_template('index.html', error=error)



@app.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')
    tem_assinatura = False

    if user_id:
        conn = sqlite3.connect("assinaturas.db")
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM assinaturas WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            email = result[0]
            tem_assinatura = verificar_assinatura_por_email(email)

    return render_template('paginaUnica.html', username=username, user_id=user_id, tem_assinatura=tem_assinatura)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# Geração de imagem
def gerar_imagem(descricao):
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=descricao,
            size="1024x1024",
            quality="standard",
            n=1
        )
        return response.data[0].url
    except Exception as e:
        return f"Erro ao gerar imagem: {str(e)}"


@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    user_id = session['user_id']

    try:
        data = request.json
        user_message = data.get('message')
        funcionalidade = data.get('funcionalidade')
        conversa_id = data.get('conversa_id')
        history = data.get('history', [])

        if not conversa_id:
            title = user_message[:20]
            conversa_id = registrar_conversa(user_id, title) if registrar_conversa else None

        salvar_mensagem(conversa_id, 'user', user_message) if salvar_mensagem else None

        if funcionalidade == 'gerar_imagem':
            url_imagem = gerar_imagem(user_message)
            if salvar_mensagem:
                salvar_mensagem(conversa_id, 'vix', url_imagem)
            if "Erro" in url_imagem:
                return jsonify({"response": url_imagem})
            return jsonify({"image_url": url_imagem, "conversa_id": conversa_id})

        instruction = "Aqui vai sua instrução do sistema"
        messages = [{"role": "system", "content": instruction}] + history + [{"role": "user", "content": user_message}]

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        reply = response.choices[0].message.content

        if salvar_mensagem:
            salvar_mensagem(conversa_id, 'vix', reply)

        return jsonify({"response": reply, "conversa_id": conversa_id})

    except Exception as e:
        print(f"Erro no chat: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/carregar_conversas', methods=['POST'])
def carregar_conversas_usuario():
    if not carregar_conversas_ordenadas:
        return jsonify({"error": "Erro ao carregar conversas"}), 500
    user_id = session.get('user_id')
    conversas = carregar_conversas_ordenadas(user_id)
    return jsonify([{"id": conv[0], "title": conv[1]} for conv in conversas])


@app.route('/carregar_mensagem', methods=['POST'])
def carregar_mensagem_view():
    try:
        conversa_id = request.json.get('conversa_id')
        if not conversa_id:
            return jsonify({"error": "Conversa ID não fornecido"}), 400

        if not carregar_mensagem:
            return jsonify({"error": "Erro ao carregar mensagens"}), 500

        historico = carregar_mensagem(conversa_id)
        return jsonify(historico)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/renomear_conversa', methods=['POST'])
def renomear():
    if not renomear_conversa:
        return jsonify({"error": "Erro ao renomear conversa"}), 500
    conversa_id = request.json.get('conversa_id')
    novo_titulo = request.json.get('novo_titulo')
    renomear_conversa(conversa_id, novo_titulo)
    return jsonify({"status": "Conversa renomeada"})


@app.route('/excluir_conversa', methods=['POST'])
def excluir_conversa_view():
    try:
        conversa_id = request.json.get('conversa_id')

        if not excluir_conversa:
            return jsonify({"error": "Erro ao excluir conversa"}), 500

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mensagens WHERE conversa_id = ?", (conversa_id,))
            cursor.execute("DELETE FROM conversas WHERE id = ?", (conversa_id,))
            conn.commit()

        return jsonify({"status": "Conversa excluída"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/carregar_historico', methods=['POST'])
def carregar_historico():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida. Nenhum JSON recebido"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID não fornecido"}), 400

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, created_at FROM conversas WHERE user_id = ?", (user_id,))
            conversas = cursor.fetchall()

            historico = []
            for conversa in conversas:
                conversa_id, title, created_at = conversa
                cursor.execute("SELECT remetente, mensagem FROM mensagens WHERE conversa_id = ?", (conversa_id,))
                mensagens = cursor.fetchall()

                historico.append({
                    "conversa_id": conversa_id,
                    "title": title,
                    "created_at": created_at,
                    "mensagens": [
                        {"remetente": msg[0], "mensagem": msg[1]} for msg in mensagens
                    ]
                })

        return jsonify(historico)

    except sqlite3.Error as db_error:
        return jsonify({"error": f"Erro no banco de dados: {str(db_error)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

@app.route("/assinatura")
def gerar_assinatura():
    preapproval_plan_id = "2c9380849154066301916d1a4b330a69"
    url = f"https://www.mercadopago.com.br/subscriptions/checkout?preapproval_plan_id={preapproval_plan_id}"
    return redirect(url)  # redireciona o cliente direto pro Mercado Pago


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Webhook recebido:", data)

    if data.get("type") == "preapproval":
        preapproval_id = data.get("data", {}).get("id")
        assinatura = sdk.preapproval().get(preapproval_id)["response"]

        email = assinatura.get("payer_email")
        status = assinatura.get("status")
        data_assinatura = assinatura.get("date_created")

        conn = sqlite3.connect("assinaturas.db")
        cursor = conn.cursor()

        # Atualiza o status do usuário com base no e-mail
        cursor.execute("""
            UPDATE assinaturas
            SET status = ?, data_assinatura = ?
            WHERE email = ?
        """, (status, data_assinatura, email))

        conn.commit()
        conn.close()

        print(f"Assinatura atualizada: {email} - {status}")

    return jsonify({"status": "recebido"}), 200


if __name__ == '__main__':
    app.run(debug=True)
