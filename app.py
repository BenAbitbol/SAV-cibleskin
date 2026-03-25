"""SAV Assistant CibleSkin - API Web (Flask)."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from sav_assistant import generate_response, load_reference_data, load_signature, save_draft

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    """Page d'accueil avec l'interface SAV."""
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Endpoint API pour generer une reponse SAV."""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Le champ 'message' est requis."}), 400

    customer_message = data["message"]
    channel = data.get("channel", "email")
    context = data.get("context", "")

    if channel not in ("email", "instagram_dm", "instagram_comment"):
        return jsonify({"error": "Canal invalide. Utilisez: email, instagram_dm, instagram_comment"}), 400

    try:
        response_text = generate_response(customer_message, channel, context)
        draft_path = save_draft(response_text, channel, customer_message)
        return jsonify({
            "response": response_text,
            "channel": channel,
            "draft_saved": str(draft_path),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/signature", methods=["GET"])
def api_signature():
    """Affiche la signature email actuelle."""
    return jsonify({"signature": load_signature()})


@app.route("/api/data", methods=["GET"])
def api_data():
    """Liste les fichiers de reference charges."""
    ref = load_reference_data()
    return jsonify({"reference_data": ref if ref else "Aucun fichier de reference."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
