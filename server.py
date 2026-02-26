from flask import Flask, request, jsonify

app = Flask(__name__)

pagamentos_registrados = {}
pagamentos_aprovados = {}


@app.route("/registrar", methods=["POST"])
def registrar():

    data = request.json
    payment_id = str(data["payment_id"])

    pagamentos_registrados[payment_id] = data

    return {"status": "ok"}


@app.route("/notify", methods=["POST"])
def notify():

    data = request.json

    if "data" not in data:
        return "OK"

    payment_id = str(data["data"]["id"])

    if payment_id in pagamentos_registrados:
        pagamentos_aprovados[payment_id] = pagamentos_registrados[payment_id]

    return "OK"


@app.route("/pendentes")
def pendentes():
    return jsonify(pagamentos_aprovados)


@app.route("/confirmar", methods=["POST"])
def confirmar():

    payment_id = request.json["payment_id"]

    pagamentos_aprovados.pop(payment_id, None)

    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
