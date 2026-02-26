from flask import Flask, request, jsonify
import mercadopago
import os

app = Flask(__name__)

sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_ACCESS_TOKEN"))

pagamentos_aprovados = []

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/notify", methods=["POST"])
def notify():
    data = request.json

    payment_id = None

    if 'data' in data and 'id' in data['data']:
        payment_id = data['data']['id']
    elif 'resource' in data:
        payment_id = data['resource'].split('/')[-1]

    if not payment_id:
        return "OK", 200

    payment_info = sdk.payment().get(payment_id)

    if payment_info["status"] != 200:
        return "OK", 200

    payment = payment_info["response"]

    if payment["status"] == "approved":
        pagamentos_aprovados.append(payment_id)

    return "OK", 200


@app.route("/pendentes", methods=["GET"])
def pendentes():
    return jsonify(pagamentos_aprovados)


@app.route("/confirmar", methods=["POST"])
def confirmar():
    data = request.json
    payment_id = data.get("payment_id")

    if payment_id in pagamentos_aprovados:
        pagamentos_aprovados.remove(payment_id)

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
