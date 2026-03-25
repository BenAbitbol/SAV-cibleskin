"""SAV Assistant CibleSkin - Base de donnees Supabase."""

import os

from supabase import create_client


def get_supabase():
    """Retourne un client Supabase."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL et SUPABASE_KEY doivent etre configures.")
    return create_client(url, key)


# --- Settings ---

def get_setting(key, default=""):
    try:
        sb = get_supabase()
        res = sb.table("settings").select("value").eq("key", key).execute()
        return res.data[0]["value"] if res.data else default
    except Exception:
        return default


def set_setting(key, value):
    sb = get_supabase()
    sb.table("settings").upsert({"key": key, "value": value}).execute()


# --- Knowledge Base ---

def get_kb_articles(category=None):
    sb = get_supabase()
    query = sb.table("knowledge_base").select("*").order("updated_at", desc=True)
    if category:
        query = query.eq("category", category)
    return query.execute().data


def get_kb_article(article_id):
    sb = get_supabase()
    res = sb.table("knowledge_base").select("*").eq("id", article_id).execute()
    return res.data[0] if res.data else None


def save_kb_article(title, content, category, article_id=None, file_url=None, file_name=None):
    sb = get_supabase()
    data = {"title": title, "content": content, "category": category}
    if file_url:
        data["file_url"] = file_url
    if file_name:
        data["file_name"] = file_name
    if article_id:
        data["id"] = article_id
        sb.table("knowledge_base").update(data).eq("id", article_id).execute()
    else:
        sb.table("knowledge_base").insert(data).execute()


def delete_kb_article(article_id):
    sb = get_supabase()
    # Supprimer le fichier associe si present
    article = get_kb_article(article_id)
    if article and article.get("file_name"):
        try:
            sb.storage.from_("files").remove([article["file_name"]])
        except Exception:
            pass
    sb.table("knowledge_base").delete().eq("id", article_id).execute()


# --- Products ---

def get_products():
    sb = get_supabase()
    return sb.table("products").select("*").order("category").order("name").execute().data


def get_product(product_id):
    sb = get_supabase()
    res = sb.table("products").select("*").eq("id", product_id).execute()
    return res.data[0] if res.data else None


def save_product(name, sku, price, description, category, in_stock, product_id=None, image_url=None):
    sb = get_supabase()
    data = {
        "name": name, "sku": sku, "price": price,
        "description": description, "category": category, "in_stock": bool(in_stock),
    }
    if image_url:
        data["image_url"] = image_url
    if product_id:
        sb.table("products").update(data).eq("id", product_id).execute()
    else:
        sb.table("products").insert(data).execute()


def delete_product(product_id):
    sb = get_supabase()
    sb.table("products").delete().eq("id", product_id).execute()


# --- Conversations ---

def save_conversation(customer_name, customer_email, channel, category,
                      customer_message, ai_response, context, status="draft"):
    sb = get_supabase()
    sb.table("conversations").insert({
        "customer_name": customer_name, "customer_email": customer_email,
        "channel": channel, "category": category,
        "customer_message": customer_message, "ai_response": ai_response,
        "context": context, "status": status,
    }).execute()


def get_conversations(limit=50, status=None, channel=None):
    sb = get_supabase()
    query = sb.table("conversations").select("*").order("created_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    if channel:
        query = query.eq("channel", channel)
    return query.execute().data


def update_conversation_status(conv_id, status):
    sb = get_supabase()
    sb.table("conversations").update({"status": status}).eq("id", conv_id).execute()


def get_conversation(conv_id):
    sb = get_supabase()
    res = sb.table("conversations").select("*").eq("id", conv_id).execute()
    return res.data[0] if res.data else None


def delete_conversation(conv_id):
    sb = get_supabase()
    sb.table("conversations").delete().eq("id", conv_id).execute()


# --- Templates ---

def get_templates():
    sb = get_supabase()
    return sb.table("templates").select("*").order("channel").order("name").execute().data


def save_template(name, channel, category, content, template_id=None):
    sb = get_supabase()
    data = {"name": name, "channel": channel, "category": category, "content": content}
    if template_id:
        sb.table("templates").update(data).eq("id", template_id).execute()
    else:
        sb.table("templates").insert(data).execute()


def delete_template(template_id):
    sb = get_supabase()
    sb.table("templates").delete().eq("id", template_id).execute()


# --- Files (Supabase Storage) ---

def upload_file(file_bytes, file_name, content_type="application/octet-stream"):
    """Upload un fichier dans Supabase Storage. Retourne l'URL publique."""
    sb = get_supabase()
    import time
    storage_path = f"{int(time.time())}_{file_name}"
    sb.storage.from_("files").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )
    url = sb.storage.from_("files").get_public_url(storage_path)
    return url, storage_path


def extract_text_from_pdf(file_bytes):
    """Extrait le texte d'un fichier PDF."""
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)
    except Exception as e:
        return f"(Erreur extraction PDF: {e})"


def analyze_image(file_bytes, file_name, media_type="image/png"):
    """Analyse une image avec Claude Vision et retourne un resume textuel."""
    import base64
    import anthropic

    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "Analyse cette image en detail pour alimenter une base de savoir "
                        "d'un service client (SAV) de la marque CibleSkin (soins de peau). "
                        "Extrais et decris :\n"
                        "- Tout texte visible (ingredients, instructions, prix, etc.)\n"
                        "- Le type de document ou visuel (packaging, brochure, capture ecran, photo produit, etc.)\n"
                        "- Les informations cles utiles pour repondre aux clients\n\n"
                        "Reponds en francais, de maniere structuree et exhaustive."
                    ),
                },
            ],
        }],
    )

    for block in response.content:
        if block.type == "text":
            return block.text
    return "(Aucune analyse disponible)"


# --- Stats ---

def get_stats():
    sb = get_supabase()
    stats = {}

    convos = sb.table("conversations").select("id, channel, status, category").execute().data
    stats["total_conversations"] = len(convos)
    stats["by_channel"] = {}
    stats["by_status"] = {}
    stats["by_category"] = {}
    for c in convos:
        ch = c.get("channel", "unknown")
        stats["by_channel"][ch] = stats["by_channel"].get(ch, 0) + 1
        st = c.get("status", "unknown")
        stats["by_status"][st] = stats["by_status"].get(st, 0) + 1
        cat = c.get("category")
        if cat:
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

    stats["total_products"] = len(sb.table("products").select("id").execute().data)
    stats["total_kb_articles"] = len(sb.table("knowledge_base").select("id").execute().data)

    return stats


def init_db():
    """Verification de connexion Supabase (les tables sont creees via schema.sql)."""
    try:
        sb = get_supabase()
        sb.table("settings").select("key").limit(1).execute()
    except Exception as e:
        print(f"[WARNING] Supabase non connecte: {e}")
