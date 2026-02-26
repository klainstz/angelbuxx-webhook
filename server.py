from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

CACHE = "pagamentos.json"

def load():
    if not os.path.exists(CACHE):
        return {}
    with open(CACHE) as f:
        return json.load(f)

def save(data):
    with open(CACHE, "w") as f:
        json.dump(data, f)


@app.route("/notify", methods=["POST"])
def notify():

    data = request.json

    payment_id = None

    if "data" in data:
        payment_id = str(data["data"]["id"])

    if not payment_id:
        return "OK"

    pagamentos = load()
    pagamentos[payment_id] = data

    save(pagamentos)

    return "OK"


@app.route("/pendentes")
def pendentes():
    return load()


@app.route("/confirmar", methods=["POST"])
def confirmar():

    pid = request.json["payment_id"]

    pagamentos = load()

    if pid in pagamentos:
        del pagamentos[pid]

    save(pagamentos)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
