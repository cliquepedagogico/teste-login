import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Seu token de acesso do Mercado Pago SANDBOX
ACCESS_TOKEN = os.getenv("MERCADO_PAGO_TOKEN")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Dados da nova conta de comprador de teste
body = {
    "site_id": "MLB",  # Brasil
    "email": "comprador_teste_@example.com"
}

response = requests.post("https://api.mercadopago.com/users/test_user", json=body, headers=headers)

if response.status_code == 201:
    data = response.json()
    print("✅ Conta de teste criada com sucesso:")
    print("🧑 Usuário:", data["email"])
    print("🔑 Senha: test_user")
    print("🆔 ID:", data["id"])
else:
    print("❌ Erro ao criar conta:", response.text)
