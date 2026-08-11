from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ET 9/21 EMA Cross 8.7.x — account 5997003, contract CON.F.US.MNQ.U26
BASE_URL    = "https://jessenia-glucosidal-hortencia.ngrok-free.dev"
ACCOUNT_ID  = "5997003"
CONTRACT_ID = "CON.F.US.MNQ.U26"

# Safety cap — a bad payload or bug should never be able to silently
# request an absurd contract count. Adjust if your real max size grows.
MAX_QTY = 10


def build_open_url(side: int, qty: int) -> str:
    return (f"{BASE_URL}/api/enter?side={side}&accountId={ACCOUNT_ID}"
            f"&contractId={CONTRACT_ID}&size={qty}&close=true&stop=0&mode=dollar")


def build_close_url() -> str:
    return f"{BASE_URL}/api/exit?accountId={ACCOUNT_ID}&contractId={CONTRACT_ID}"


def parse_quantity(data: dict) -> int:
    """Reads 'quantity' from the payload, defaults to 1, clamps to [1, MAX_QTY]."""
    raw = data.get("quantity", 1)
    try:
        qty = int(float(raw))
    except (TypeError, ValueError):
        logging.warning("Non-numeric quantity received: %r — defaulting to 1", raw)
        return 1

    if qty < 1:
        logging.warning("Quantity %d < 1 — clamping to 1", qty)
        return 1
    if qty > MAX_QTY:
        logging.warning("Quantity %d exceeds MAX_QTY=%d — clamping to %d", qty, MAX_QTY, MAX_QTY)
        return MAX_QTY
    return qty


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    data = request.get_json(force=True, silent=True) or {}
    logging.info("Received payload: %s", data)

    sentiment = data.get("sentiment")
    qty = parse_quantity(data)

    if sentiment == "long":
        target = build_open_url(side=0, qty=qty)
    elif sentiment == "short":
        target = build_open_url(side=1, qty=qty)
    elif sentiment == "flat":
        target = build_close_url()  # closes the whole position regardless of qty
    else:
        logging.warning("Unrecognized sentiment: %s", sentiment)
        return jsonify({"error": "unrecognized sentiment", "data": data}), 400

    try:
        r = requests.post(target, timeout=10)
        logging.info("Routed to %s -> status %s, body %s", target, r.status_code, r.text[:200])
        return jsonify({
            "routed_sentiment": sentiment,
            "quantity_used": qty,
            "upstream_status": r.status_code,
            "upstream_body": r.text
        }), 200
    except requests.RequestException as e:
        logging.error("Upstream request failed: %s", e)
        return jsonify({"error": "upstream request failed", "detail": str(e)}), 502


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
