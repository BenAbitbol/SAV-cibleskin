"""SAV Assistant CibleSkin - Application web Flask."""

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

from database import (
    analyze_image,
    delete_conversation,
    delete_kb_article,
    delete_product,
    delete_template,
    extract_text_from_pdf,
    get_conversation,
    get_conversations,
    get_kb_article,
    get_kb_articles,
    get_product,
    get_products,
    get_setting,
    get_stats,
    get_templates,
    init_db,
    save_conversation,
    save_kb_article,
    save_product,
    save_template,
    set_setting,
    update_conversation_status,
    upload_file,
)
from sav_assistant import generate_response

load_dotenv()

app = Flask(__name__)

# Init DB en lazy (pas au demarrage pour eviter le timeout Render)


@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": f"Erreur serveur: {e}"}), 500
    return render_template("base.html", page="error"), 500


@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint introuvable"}), 404
    return redirect(url_for("index"))


# --- Pages principales ---

@app.route("/")
def index():
    try:
        stats = get_stats()
        recent = get_conversations(limit=5)
    except Exception as e:
        stats = {"total_conversations": 0, "by_channel": {}, "by_status": {}, "by_category": {},
                 "total_products": 0, "total_kb_articles": 0, "error": str(e)}
        recent = []
    return render_template("dashboard.html", stats=stats, recent=recent, page="dashboard")


@app.route("/brief")
def brief():
    return render_template("brief.html", page="brief")


@app.route("/assistant")
def assistant():
    templates = get_templates()
    return render_template("assistant.html", templates=templates, page="assistant")


@app.route("/historique")
def historique():
    status = request.args.get("status")
    channel = request.args.get("channel")
    convos = get_conversations(limit=100, status=status, channel=channel)
    return render_template("historique.html", conversations=convos, page="historique",
                           filter_status=status, filter_channel=channel)


@app.route("/historique/<int:conv_id>")
def conversation_detail(conv_id):
    conv = get_conversation(conv_id)
    if not conv:
        return redirect(url_for("historique"))
    return render_template("conversation_detail.html", conv=conv, page="historique")


@app.route("/base-connaissances")
def knowledge_base():
    category = request.args.get("category")
    try:
        articles = get_kb_articles(category=category)
        categories = sorted(set(a["category"] for a in get_kb_articles()))
    except Exception as e:
        articles = []
        categories = []
        app.logger.error(f"Erreur KB: {e}")
    return render_template("knowledge_base.html", articles=articles, categories=categories,
                           page="kb", filter_category=category)


@app.route("/produits")
def produits():
    products = get_products()
    return render_template("products.html", products=products, page="products")


@app.route("/parametres")
def parametres():
    agent_name = get_setting("agent_name", "Lina")
    brand_name = get_setting("brand_name", "Cible Skin")
    sav_email = get_setting("sav_email", "")
    website = get_setting("website", "https://www.cibleskin.com")
    instagram = get_setting("instagram", "")
    return render_template("settings.html", page="settings",
                           agent_name=agent_name, brand_name=brand_name,
                           sav_email=sav_email, website=website, instagram=instagram)


# --- API Endpoints ---

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Le champ 'message' est requis."}), 400

    channel = data.get("channel", "email")
    if channel not in ("email", "instagram_dm", "instagram_comment"):
        return jsonify({"error": "Canal invalide."}), 400

    # Verifier que la cle API est configuree
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"error": "Cle API Anthropic non configuree. Ajoutez ANTHROPIC_API_KEY dans les variables d'environnement."}), 500

    try:
        response_text = generate_response(
            customer_message=data["message"],
            channel=channel,
            context=data.get("context", ""),
            customer_name=data.get("customer_name", ""),
            tone=data.get("tone", "professionnel"),
        )
        save_conversation(
            customer_name=data.get("customer_name", ""),
            customer_email=data.get("customer_email", ""),
            channel=channel,
            category=data.get("category", ""),
            customer_message=data["message"],
            ai_response=response_text,
            context=data.get("context", ""),
        )
        return jsonify({"response": response_text, "channel": channel})
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Erreur generation: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500


@app.route("/api/conversation/<int:conv_id>/status", methods=["POST"])
def api_update_status(conv_id):
    data = request.get_json()
    update_conversation_status(conv_id, data["status"])
    return jsonify({"ok": True})


@app.route("/api/conversation/<int:conv_id>", methods=["DELETE"])
def api_delete_conversation(conv_id):
    delete_conversation(conv_id)
    return jsonify({"ok": True})


@app.route("/api/kb", methods=["POST"])
def api_save_kb():
    data = request.get_json()
    save_kb_article(data["title"], data["content"], data["category"], data.get("id"),
                    data.get("file_url"), data.get("file_name"))
    return jsonify({"ok": True})


@app.route("/api/upload", methods=["POST"])
def api_upload_file():
    """Upload un fichier (PDF, image, texte) et extrait le contenu si possible."""
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier envoye"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Nom de fichier vide"}), 400

    file_bytes = f.read()
    content_type = f.content_type or "application/octet-stream"

    try:
        file_url, storage_path = upload_file(file_bytes, f.filename, content_type)

        # Extraire le texte selon le type de fichier
        extracted_text = ""
        lower_name = f.filename.lower()
        if lower_name.endswith(".pdf"):
            extracted_text = extract_text_from_pdf(file_bytes)
        elif lower_name.endswith((".txt", ".md", ".csv")):
            extracted_text = file_bytes.decode("utf-8", errors="replace")
        elif lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            # Analyse d'image par Claude Vision
            media_types = {
                ".png": "image/png", ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg", ".webp": "image/webp",
                ".gif": "image/gif",
            }
            ext = "." + lower_name.rsplit(".", 1)[-1]
            media_type = media_types.get(ext, "image/png")
            extracted_text = analyze_image(file_bytes, f.filename, media_type)

        return jsonify({
            "file_url": file_url,
            "file_name": storage_path,
            "extracted_text": extracted_text,
            "original_name": f.filename,
        })
    except Exception as e:
        return jsonify({"error": f"Erreur upload: {e}"}), 500


@app.route("/api/kb/<int:article_id>", methods=["GET"])
def api_get_kb(article_id):
    article = get_kb_article(article_id)
    return jsonify(article) if article else (jsonify({"error": "Not found"}), 404)


@app.route("/api/kb/<int:article_id>", methods=["DELETE"])
def api_delete_kb(article_id):
    delete_kb_article(article_id)
    return jsonify({"ok": True})


@app.route("/api/product", methods=["POST"])
def api_save_product():
    data = request.get_json()
    save_product(
        data["name"], data.get("sku", ""), data.get("price", 0),
        data.get("description", ""), data.get("category", ""),
        data.get("in_stock", 1), data.get("id"),
    )
    return jsonify({"ok": True})


@app.route("/api/product/<int:product_id>", methods=["GET"])
def api_get_product(product_id):
    product = get_product(product_id)
    return jsonify(product) if product else (jsonify({"error": "Not found"}), 404)


@app.route("/api/product/<int:product_id>", methods=["DELETE"])
def api_delete_product(product_id):
    delete_product(product_id)
    return jsonify({"ok": True})


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json()
    for key, value in data.items():
        set_setting(key, value)
    return jsonify({"ok": True})


@app.route("/api/template", methods=["POST"])
def api_save_template():
    data = request.get_json()
    save_template(data["name"], data["channel"], data.get("category", ""), data["content"], data.get("id"))
    return jsonify({"ok": True})


@app.route("/api/template/<int:template_id>", methods=["DELETE"])
def api_delete_template(template_id):
    delete_template(template_id)
    return jsonify({"ok": True})


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/health")
def api_health():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    sb_url = os.environ.get("SUPABASE_URL", "")
    sb_key = os.environ.get("SUPABASE_KEY", "")
    sb_ok = False
    if sb_url and sb_key:
        try:
            from database import get_supabase
            get_supabase().table("settings").select("key").limit(1).execute()
            sb_ok = True
        except Exception:
            pass
    return jsonify({
        "status": "ok",
        "api_key_configured": bool(api_key),
        "supabase_configured": bool(sb_url and sb_key),
        "supabase_connected": sb_ok,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
