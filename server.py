"""
AngelBuxx — server.py (Render)
Persiste dados em arquivo /tmp. O cog pagamentos.py no bot
consulta o MP diretamente como backup, então o Render é opcional.
"""

import os, json, mercadopago
from flask import Flask, request, jsonify

app = Flask(__name__)
MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
DB_FILE = "/tmp/pag.json"

def _load():
    try:
        with open(DB_FILE) as f: return json.load(f)
    except: return {"r": {}, "a": {}}

def _save(d):
    try:
        with open(DB_FILE, "w") as f: json.dump(d, f)
    except Exception as e: print(f"[save] {e}")

def _processar(pid_raw):
    pid = str(pid_raw).strip()
    db  = _load()
    print(f"[notify] id={pid} registrados={list(db['r'].keys())}")
    key = pid if pid in db["r"] else next(
        (k for k in db["r"] if str(int(k)) == str(int(pid))), None) if pid.isdigit() else None
    if not key:
        print(f"[notify] {pid} não registrado")
        return
    try:
        status = mercadopago.SDK(MP_ACCESS_TOKEN).payment().get(key)["response"].get("status","")
        print(f"[notify] status={status}")
    except Exception as e:
        print(f"[notify] erro MP: {e}"); return
    if status == "approved":
        db["a"][key] = db["r"][key]; _save(db)
        print(f"[notify] ✅ aprovado: {key}")

@app.route("/registrar", methods=["POST"])
def registrar():
    d = request.json or {}
    pid = str(d.get("payment_id","")).strip()
    if not pid: return {"status":"erro"},400
    db = _load()
    db["r"][pid] = {"payment_id":pid,"canal_pag_id":d.get("canal_pag_id"),"guild_id":d.get("guild_id")}
    _save(db)
    print(f"[registrar] {pid}")
    return {"status":"ok"}

@app.route("/notify", methods=["POST","GET"])
@app.route("/notify/notify", methods=["POST","GET"])
def notify():
    print(f"[notify] args={dict(request.args)} body={request.get_data(as_text=True)[:200]}")
    d   = request.get_json(silent=True) or {}
    pid = (str(d["data"]["id"]) if "data" in d and "id" in d["data"] else
           request.args.get("id") or request.args.get("data.id") or
           str(d["id"]) if "id" in d else None)
    if pid: _processar(pid)
    return "OK", 200

@app.route("/pendentes")
def pendentes():
    db = _load()
    print(f"[pendentes] aprovados={list(db['a'].keys())}")
    return jsonify(db["a"])

@app.route("/confirmar", methods=["POST"])
def confirmar():
    pid = str((request.json or {}).get("payment_id","")).strip()
    db  = _load()
    db["a"].pop(pid,None); db["r"].pop(pid,None); _save(db)
    return {"status":"ok"}

@app.route("/aprovar/<pid>")
def aprovar(pid):
    db = _load()
    key = pid if pid in db["r"] else next(
        (k for k in db["r"] if str(int(k))==str(int(pid))), None) if pid.isdigit() else None
    if not key: return jsonify({"status":"nao_encontrado","registrados":list(db["r"].keys())}),404
    db["a"][key]=db["r"][key]; _save(db)
    return jsonify({"status":"aprovado","id":key})

@app.route("/")
def health():
    db = _load()
    return jsonify({"status":"online","registrados":len(db["r"]),"aprovados":len(db["a"]),"ids":list(db["r"].keys())})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
