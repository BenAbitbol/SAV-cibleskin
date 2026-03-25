"""SAV Assistant CibleSkin - Moteur IA avec l'API Claude."""

from pathlib import Path

import anthropic

from database import get_kb_articles, get_products, get_setting


def build_system_prompt():
    """Construit le system prompt avec les donnees de reference depuis la DB."""
    instructions = Path(__file__).parent / "CLAUDE.md"
    system = instructions.read_text(encoding="utf-8")

    # Charger les articles de la base de connaissances
    articles = get_kb_articles()
    if articles:
        system += "\n\n---\n\n## DONNEES DE REFERENCE (Base de connaissances)\n\n"
        for art in articles:
            system += f"### [{art['category']}] {art['title']}\n{art['content']}\n\n"
    else:
        system += "\n\n---\n\n## DONNEES DE REFERENCE\n\n(Aucun article dans la base de connaissances)\n"

    # Charger les produits
    products = get_products()
    if products:
        system += "\n## CATALOGUE PRODUITS\n\n"
        for p in products:
            stock = "En stock" if p["in_stock"] else "Rupture"
            price_str = f"{p['price']:.2f} EUR" if p["price"] else "Prix non defini"
            system += f"- **{p['name']}** (SKU: {p['sku'] or 'N/A'}) - {price_str} - {stock}\n"
            if p["description"]:
                system += f"  {p['description']}\n"

    # Charger la signature
    signature = get_setting("signature", "")
    if signature:
        system += f"\n\n## SIGNATURE EMAIL ACTUELLE\n\n{signature}"

    return system


def generate_response(customer_message, channel="email", context="", customer_name="", customer_email="", tone="professionnel"):
    """Genere une reponse SAV via l'API Claude."""
    client = anthropic.Anthropic()
    system_prompt = build_system_prompt()

    channel_labels = {
        "email": "EMAIL",
        "instagram_dm": "INSTAGRAM DM",
        "instagram_comment": "INSTAGRAM COMMENTAIRE PUBLIC",
    }

    channel_instruction = {
        "email": "Genere une reponse EMAIL complete avec objet. Utilise la signature.",
        "instagram_dm": "Genere une reponse Instagram DM (courte, chaleureuse, 3-5 lignes).",
        "instagram_comment": (
            "Genere une reponse Instagram COMMENTAIRE PUBLIC "
            "(2-3 lignes, ne jamais partager d'infos sensibles, "
            "rediriger en DM si necessaire)."
        ),
    }

    parts = [f"Canal : {channel_labels.get(channel, 'EMAIL')}"]
    if customer_name:
        parts.append(f"Nom du client : {customer_name}")
    if customer_email:
        parts.append(f"Email du client : {customer_email}")
    if context:
        parts.append(f"Contexte supplementaire : {context}")
    parts.append(f"\nMessage client :\n---\n{customer_message}\n---")
    instruction = channel_instruction.get(channel, channel_instruction["email"])
    parts.append(f"\nInstruction : {instruction}")

    user_content = "\n".join(parts)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    result_parts = []
    for block in response.content:
        if block.type == "text":
            result_parts.append(block.text)

    return "\n".join(result_parts)
