from flask import Flask, render_template, request, jsonify
import openai
from dotenv import load_dotenv
import os
import sqlite3
import subprocess

# Importa funções do arquivo db.py (Verifique se ele está no mesmo diretório)
try:
    from db import (
        registrar_conversa, salvar_mensagem, carregar_conversas_ordenadas, 
        carregar_mensagem, renomear_conversa, excluir_conversa
    )
except ImportError as e:
    print(f"Erro ao importar funções de 'db.py': {e}")
    registrar_conversa = salvar_mensagem = carregar_conversas_ordenadas = carregar_mensagem = renomear_conversa = excluir_conversa = None

# Inicializa o Flask
app = Flask(__name__)

# Carregar variáveis de ambiente
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)


@app.route('/executar', methods=['GET'])
def executar_python():
    try:
        caminho_script = os.path.join(os.path.dirname(__file__), "posLogin", "app.py")  # Caminho correto
        resultado = subprocess.run(["python", caminho_script], capture_output=True, text=True)
        
        return jsonify({"success": True, "message": "Script executado!", "output": resultado.stdout})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

    


# 🔹 Função para gerar imagens com OpenAI
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

# 🔹 Página inicial
@app.route("/", methods=["GET"])
def index():
    user_id = request.args.get("user_id")
    return render_template("index.html", user_id=user_id)

# 🔹 Rota principal do chat
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_id = data.get('user_id')
        user_message = data.get('message')
        funcionalidade = data.get('funcionalidade')
        conversa_id = data.get('conversa_id')
        history = data.get('history', [])

        if not conversa_id:
            title = user_message[:20]  
            conversa_id = registrar_conversa(user_id, title) if registrar_conversa else None

        salvar_mensagem(conversa_id, 'user', user_message) if salvar_mensagem else None

        # Se for para gerar imagem
        if funcionalidade == 'gerar_imagem':
            url_imagem = gerar_imagem(user_message)
            if salvar_mensagem:
                salvar_mensagem(conversa_id, 'vix', url_imagem)
            if "Erro" in url_imagem:
                return jsonify({"response": url_imagem})
            return jsonify({"image_url": url_imagem, "conversa_id": conversa_id})

        # Geração de texto pela OpenAI
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

# 🔹 Carregar conversas do usuário
@app.route('/carregar_conversas', methods=['POST'])
def carregar_conversas_usuario():
    if not carregar_conversas_ordenadas:
        return jsonify({"error": "Erro ao carregar conversas"}), 500
    user_id = request.json.get('user_id')
    conversas = carregar_conversas_ordenadas(user_id)
    return jsonify([{"id": conv[0], "title": conv[1]} for conv in conversas])

# 🔹 Carregar mensagens de uma conversa
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

# 🔹 Renomear conversa
@app.route('/renomear_conversa', methods=['POST'])
def renomear():
    if not renomear_conversa:
        return jsonify({"error": "Erro ao renomear conversa"}), 500
    conversa_id = request.json.get('conversa_id')
    novo_titulo = request.json.get('novo_titulo')
    renomear_conversa(conversa_id, novo_titulo)
    return jsonify({"status": "Conversa renomeada"})

# 🔹 Excluir conversa e mensagens associadas
@app.route('/excluir_conversa', methods=['POST'])
def excluir_conversa_view():
    try:
        conversa_id = request.json.get('conversa_id')

        if not excluir_conversa:
            return jsonify({"error": "Erro ao excluir conversa"}), 500

        with sqlite3.connect('historico.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mensagens WHERE conversa_id = ?", (conversa_id,))
            cursor.execute("DELETE FROM conversas WHERE id = ?", (conversa_id,))
            conn.commit()

        return jsonify({"status": "Conversa excluída"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Carregar histórico completo do usuário

@app.route('/carregar_historico', methods=['POST'])
def carregar_historico():
    try:
        # ✅ Recebe o JSON do JavaScript corretamente
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Requisição inválida. Nenhum JSON recebido"}), 400

        user_id = data.get('user_id')

        # ✅ Valida se user_id foi enviado e se é um número válido
        if not user_id:
            return jsonify({"error": "User ID não fornecido"}), 400

        try:
            user_id = int(user_id)  # Converte para inteiro, garantindo que seja válido
        except ValueError:
            return jsonify({"error": "User ID inválido"}), 400

        print(f"✅ Recebendo histórico para user_id: {user_id}")  # Debug

        with sqlite3.connect("historico.db") as conn:
            cursor = conn.cursor()

            # 🔹 Buscar todas as conversas do usuário
            cursor.execute("SELECT id, title, created_at FROM conversas WHERE user_id = ?", (user_id,))
            conversas = cursor.fetchall()

            historico = []

            for conversa in conversas:
                conversa_id, title, created_at = conversa

                # 🔹 Buscar todas as mensagens associadas a essa conversa
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

        print(f"✅ Histórico carregado com sucesso para user_id {user_id}")  # Debug
        return jsonify(historico)

    except sqlite3.Error as db_error:
        print(f"❌ Erro no banco de dados: {str(db_error)}")
        return jsonify({"error": f"Erro no banco de dados: {str(db_error)}"}), 500

    except Exception as e:
        print(f"❌ Erro inesperado ao carregar histórico: {str(e)}")
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

# 🔹 Iniciar o servidor Flask
if __name__ == '__main__':
    app.run(debug=True)
