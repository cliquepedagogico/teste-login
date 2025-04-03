import requests
from datetime import datetime, timedelta

@app.route('/criar_assinatura', methods=['POST'])
def criar_assinatura():
    access_token = "TEST-5858193927098300-040318-fbc4451721a6ac67552ba0cd96b97f12-2367358847"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    hoje = datetime.now()
    um_ano = hoje + timedelta(days=365)

    data = {
        "reason": "Assinatura Premium - Mensal",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": 1.00,
            "currency_id": "BRL",
            "start_date": hoje.isoformat(),
            "end_date": um_ano.isoformat()
        },
        "back_url": "https://teste-login-0hdz.onrender.com",
        "payer_email": "email-do-cliente@exemplo.com"  # opcional
    }

    response = requests.post("https://api.mercadopago.com/preapproval", json=data, headers=headers)
    result = response.json()
    return redirect(result["init_point"])
