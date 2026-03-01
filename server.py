"""
AngelBuxx — server.py (Render)
Rotas:
  POST /registrar        ← bot registra pagamento criado
  POST /notify           ← Mercado Pago chama quando status muda
  GET  /pendentes        ← bot consulta pagamentos aprovados
  POST /confirmar        ← bot confirma que processou
  GET  /                 ← health check / keep-alive
"""

import os
import mercadopago
from flask import Flask, request, jsonify

app = Flask(__name__)

MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

# { payment_id: { payment_id, canal_pag_id, guild_id } }
pagamentos_registrados: dict = {}
pagamentos_aprovados:   dict = {}


@app.route("/registrar", methods=["POST"])
def registrar():
    """Bot chama ao criar o pagamento Pix."""
    data       = request.json or {}
    payment_id = str(data.get("payment_id", ""))
    if not payment_id:
        return {"status": "erro", "msg": "payment_id ausente"}, 400

    pagamentos_registrados[payment_id] = {
        "payment_id":   payment_id,
        "canal_pag_id": data.get("canal_pag_id"),
        "guild_id":     data.get("guild_id"),
    }
    print(f"[registrar] Pagamento registrado: {payment_id}")
    return {"status": "ok"}


@app.route("/notify", methods=["POST"])
def notify():
    """
    Webhook do Mercado Pago.
    MP envia: { "action": "payment.updated", "data": { "id": "123" } }
    ou query params: ?id=123&topic=payment
    """
    # Tenta pegar o ID via body JSON
    data = request.json or {}
    payment_id = None

    if "data" in data and "id" in data["data"]:
        payment_id = str(data["data"]["id"])
    # Fallback: query param (formato antigo do MP)
    elif request.args.get("id"):
        payment_id = str(request.args.get("id"))

    if not payment_id:
        return "OK"

    # Só processa se o bot registrou esse pagamento
    if payment_id not in pagamentos_registrados:
        print(f"[notify] ID {payment_id} não registrado, ignorando.")
        return "OK"

    # Consulta a API do MP para confirmar status real
    try:
        sdk    = mercadopago.SDK(MP_ACCESS_TOKEN)
        result = sdk.payment().get(payment_id)
        status = result["response"].get("status", "")
        print(f"[notify] Pagamento {payment_id} status: {status}")
    except Exception as e:
        print(f"[notify] Erro ao consultar MP: {e}")
        return "OK"

    if status == "approved":
        pagamentos_aprovados[payment_id] = pagamentos_registrados[payment_id]
        print(f"[notify] ✅ Pagamento aprovado: {payment_id}")

    return "OK"


@app.route("/pendentes")
def pendentes():
    """Bot consulta a cada 15s."""
    return jsonify(pagamentos_aprovados)


@app.route("/confirmar", methods=["POST"])
def confirmar():
    """Bot chama após processar, removendo da fila."""
    data       = request.json or {}
    payment_id = str(data.get("payment_id", ""))
    pagamentos_aprovados.pop(payment_id, None)
    pagamentos_registrados.pop(payment_id, None)
    print(f"[confirmar] Pagamento removido da fila: {payment_id}")
    return {"status": "ok"}


@app.route("/")
def health():
    return {"status": "online", "registrados": len(pagamentos_registrados),
            "aprovados": len(pagamentos_aprovados)}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
