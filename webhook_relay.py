from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ET 9/21 EMA Cross 8.7.x — account 5997003, contract CON.F.US.MNQ.U26
OPEN_LONG_URL  = "https://jessenia-glucosidal-hortencia.ngrok-free.dev/api/enter?side=0&accountId=5997003&contractId=CON.F.US.MNQ.U26&size=1&close=true&stop=0&mode=dollar"
OPEN_SHORT_URL = "https://jessenia-glucosidal-hortencia.ngrok-free.dev/api/enter?side=1&accountId=5997003&contractId=CON.F.US.MNQ.U26&size=1&close=true&stop=0&mode=dollar"
CLOSE_URL      = "https://jessenia-glucosidal-hortencia.ngrok-free.dev/api/exit?accountId=5997003&contractId=CON.F.US.MNQ.U26"


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    data = request.get_json(force=True, silent=True) or {}
    logging.info("Received payload: %s", data)

    # "sentiment" is unambiguous (long/short/flat), unlike "action" (buy/sell),
    # which means the same thing for both a short entry and a long exit.
    sentiment = data.get("sentiment")

    if sentiment == "long":
        target = OPEN_LONG_URL
    elif sentiment == "short":
        target = OPEN_SHORT_URL
    elif sentiment == "flat":
        target = CLOSE_URL
    else:
        logging.warning("Unrecognized sentiment: %s", sentiment)
        return jsonify({"error": "unrecognized sentiment", "data": data}), 400

    try:
        r = requests.post(target, timeout=10)
        logging.info("Routed to %s -> status %s, body %s", target, r.status_code, r.text[:200])
        return jsonify({
            "routed_sentiment": sentiment,
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
