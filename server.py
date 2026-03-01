import os
import mercadopago
from flask import Flask, request, jsonify

app = Flask(__name__)

MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

pagamentos_registrados = {}
pagamentos_aprovados   = {}


@app.route("/registrar", methods=["POST"])
def registrar():
    data       = request.json
    payment_id = str(data["payment_id"])
    pagamentos_registrados[payment_id] = {
        "payment_id":   payment_id,
        "canal_pag_id": data["canal_pag_id"],
        "guild_id":     data["guild_id"],
    }
    return {"status": "ok"}


@app.route("/notify", methods=["POST"])
def notify():
    data = request.json or {}
    if "data" not in data:
        return "OK"

    payment_id = str(data["data"]["id"])
    if payment_id not in pagamentos_registrados:
        return "OK"

    try:
        sdk    = mercadopago.SDK(MP_ACCESS_TOKEN)
        result = sdk.payment().get(payment_id)
        status = result["response"].get("status", "")
    except Exception as e:
        print(f"[notify] Erro ao consultar MP: {e}")
        return "OK"

    if status == "approved":
        pagamentos_aprovados[payment_id] = pagamentos_registrados[payment_id]
        print(f"[notify] Pagamento aprovado: {payment_id}")

    return "OK"


@app.route("/pendentes")
def pendentes():
    return jsonify(pagamentos_aprovados)


@app.route("/confirmar", methods=["POST"])
def confirmar():
    payment_id = str(request.json["payment_id"])
    pagamentos_aprovados.pop(payment_id, None)
    pagamentos_registrados.pop(payment_id, None)
    return {"status": "ok"}


@app.route("/")
def health():
    return {"status": "online"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
