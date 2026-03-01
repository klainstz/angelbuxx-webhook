"""
AngelBuxx — server.py (Render)
Usa arquivo JSON para persistir pagamentos entre reinicios do Render.
"""

import os
import json
import mercadopago
from flask import Flask, request, jsonify

app = Flask(__name__)

MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
DB_FILE = "/tmp/pagamentos.json"


def _load():
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except Exception:
        return {"registrados": {}, "aprovados": {}}

def _save(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[save] {e}")


@app.route("/registrar", methods=["POST"])
def registrar():
    data       = request.json or {}
    payment_id = str(data.get("payment_id", "")).strip()
    if not payment_id:
        return {"status": "erro", "msg": "payment_id ausente"}, 400
    db = _load()
    db["registrados"][payment_id] = {
        "payment_id":   payment_id,
        "canal_pag_id": data.get("canal_pag_id"),
        "guild_id":     data.get("guild_id"),
    }
    _save(db)
    print(f"[registrar] ✅ {payment_id}")
    return {"status": "ok"}


def _processar_notify(payment_id_raw):
    payment_id = str(payment_id_raw).strip()
    db         = _load()
    registrados = db.get("registrados", {})
    aprovados   = db.get("aprovados", {})

    print(f"[notify] Recebido id={payment_id!r}")
    print(f"[notify] Registrados: {list(registrados.keys())}")

    # Match direto ou por int
    found_key = None
    if payment_id in registrados:
        found_key = payment_id
    else:
        try:
            pid_int = int(payment_id)
            for k in registrados:
                if int(k) == pid_int:
                    found_key = k
                    break
        except Exception:
            pass

    if not found_key:
        print(f"[notify] ID {payment_id!r} não registrado, ignorando.")
        return

    try:
        sdk    = mercadopago.SDK(MP_ACCESS_TOKEN)
        result = sdk.payment().get(found_key)
        resp   = result.get("response", {})
        status = resp.get("status", "")
        print(f"[notify] Status MP: {status!r}")
    except Exception as e:
        print(f"[notify] Erro MP: {e}")
        return

    if status == "approved":
        aprovados[found_key] = registrados[found_key]
        db["aprovados"] = aprovados
        _save(db)
        print(f"[notify] ✅ APROVADO: {found_key}")


@app.route("/notify", methods=["POST", "GET"])
def notify():
    print(f"[notify] method={request.method} args={dict(request.args)} body={request.get_data(as_text=True)[:300]}")
    data       = request.get_json(silent=True) or {}
    payment_id = None

    if "data" in data and "id" in data["data"]:
        payment_id = str(data["data"]["id"])
    elif request.args.get("id"):
        payment_id = str(request.args.get("id"))
    elif request.args.get("data.id"):
        payment_id = str(request.args.get("data.id"))
    elif "id" in data:
        payment_id = str(data["id"])

    print(f"[notify] payment_id extraído: {payment_id!r}")
    if payment_id:
        _processar_notify(payment_id)
    return "OK", 200


@app.route("/notify/notify", methods=["POST", "GET"])
def notify_dup():
    return notify()


@app.route("/pendentes")
def pendentes():
    db = _load()
    ap = db.get("aprovados", {})
    print(f"[pendentes] aprovados={list(ap.keys())}")
    return jsonify(ap)


@app.route("/confirmar", methods=["POST"])
def confirmar():
    data       = request.json or {}
    payment_id = str(data.get("payment_id", "")).strip()
    db         = _load()
    db["aprovados"].pop(payment_id, None)
    db["registrados"].pop(payment_id, None)
    _save(db)
    print(f"[confirmar] Removido: {payment_id}")
    return {"status": "ok"}


@app.route("/aprovar/<payment_id>")
def aprovar_manual(payment_id):
    """Aprovação manual para testes."""
    db          = _load()
    registrados = db.get("registrados", {})
    aprovados   = db.get("aprovados", {})

    found_key = None
    if payment_id in registrados:
        found_key = payment_id
    else:
        try:
            pid_int = int(payment_id)
            for k in registrados:
                if int(k) == pid_int:
                    found_key = k
                    break
        except Exception:
            pass

    if not found_key:
        return jsonify({"status": "nao_encontrado",
                        "registrados": list(registrados.keys())}), 404

    aprovados[found_key] = registrados[found_key]
    db["aprovados"] = aprovados
    _save(db)
    return jsonify({"status": "aprovado", "payment_id": found_key})


@app.route("/")
def health():
    db = _load()
    return jsonify({
        "status":           "online",
        "registrados":      len(db.get("registrados", {})),
        "aprovados":        len(db.get("aprovados", {})),
        "ids_registrados":  list(db.get("registrados", {}).keys()),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
