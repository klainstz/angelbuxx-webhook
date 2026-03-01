"""
AngelBuxx — server.py (Render)
"""

import os
import mercadopago
from flask import Flask, request, jsonify

app = Flask(__name__)

MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")

pagamentos_registrados: dict = {}
pagamentos_aprovados:   dict = {}


@app.route("/registrar", methods=["POST"])
def registrar():
    data       = request.json or {}
    payment_id = str(data.get("payment_id", ""))
    if not payment_id:
        return {"status": "erro", "msg": "payment_id ausente"}, 400
    pagamentos_registrados[payment_id] = {
        "payment_id":   payment_id,
        "canal_pag_id": data.get("canal_pag_id"),
        "guild_id":     data.get("guild_id"),
    }
    print(f"[registrar] ✅ {payment_id}")
    return {"status": "ok"}


def _processar_notify(payment_id_raw):
    """Lógica central do notify — chamada por todas as rotas de webhook."""
    payment_id = str(payment_id_raw).strip()
    print(f"[notify] Recebido id={payment_id!r}")
    print(f"[notify] Registrados: {list(pagamentos_registrados.keys())}")

    # Busca flexível: tenta match direto e também sem zeros à esquerda etc
    found_key = None
    if payment_id in pagamentos_registrados:
        found_key = payment_id
    else:
        # Tenta converter para int e comparar (resolve diferença de tipo str/int)
        try:
            pid_int = int(payment_id)
            for k in pagamentos_registrados:
                if int(k) == pid_int:
                    found_key = k
                    break
        except Exception:
            pass

    if not found_key:
        print(f"[notify] ID {payment_id!r} não encontrado nos registrados, ignorando.")
        return

    try:
        sdk    = mercadopago.SDK(MP_ACCESS_TOKEN)
        result = sdk.payment().get(found_key)
        resp   = result.get("response", {})
        status = resp.get("status", "")
        print(f"[notify] Status MP para {found_key}: {status!r}")
    except Exception as e:
        print(f"[notify] Erro MP: {e}")
        return

    if status == "approved":
        pagamentos_aprovados[found_key] = pagamentos_registrados[found_key]
        print(f"[notify] ✅ APROVADO: {found_key}")


@app.route("/notify", methods=["POST", "GET"])
def notify():
    # Loga tudo para debug
    print(f"[notify] method={request.method} args={dict(request.args)} body={request.get_data(as_text=True)[:300]}")

    data       = request.get_json(silent=True) or {}
    payment_id = None

    # Formato novo do MP: {"action":"payment.updated","data":{"id":"123"}}
    if "data" in data and "id" in data["data"]:
        payment_id = str(data["data"]["id"])
    # Formato query param: ?id=123&topic=payment
    elif request.args.get("id"):
        payment_id = str(request.args.get("id"))
    # Formato antigo: {"id": 123}
    elif "id" in data:
        payment_id = str(data["id"])

    if payment_id:
        _processar_notify(payment_id)
    return "OK", 200


# Aceita também /notify/notify caso o MP esteja mandando com prefixo duplicado
@app.route("/notify/notify", methods=["POST", "GET"])
def notify_dup():
    return notify()


@app.route("/pendentes")
def pendentes():
    print(f"[pendentes] aprovados={list(pagamentos_aprovados.keys())}")
    return jsonify(pagamentos_aprovados)


@app.route("/confirmar", methods=["POST"])
def confirmar():
    data       = request.json or {}
    payment_id = str(data.get("payment_id", ""))
    pagamentos_aprovados.pop(payment_id, None)
    pagamentos_registrados.pop(payment_id, None)
    print(f"[confirmar] Removido: {payment_id}")
    return {"status": "ok"}


@app.route("/aprovar/<payment_id>", methods=["GET"])
def aprovar_manual(payment_id):
    """Rota de teste — aprova manualmente um pagamento registrado."""
    if payment_id in pagamentos_registrados:
        pagamentos_aprovados[payment_id] = pagamentos_registrados[payment_id]
        return {"status": "aprovado", "payment_id": payment_id}
    return {"status": "nao_encontrado", "registrados": list(pagamentos_registrados.keys())}, 404


@app.route("/")
def health():
    return jsonify({"status": "online",
                    "registrados": len(pagamentos_registrados),
                    "aprovados":   len(pagamentos_aprovados),
                    "ids_registrados": list(pagamentos_registrados.keys())})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
