"""SAV Assistant CibleSkin - Moteur IA avec l'API Claude."""

from pathlib import Path

import anthropic

from database import get_kb_articles, get_products, get_setting


def build_system_prompt():
    """Construit le system prompt avec les donnees de reference depuis la DB."""
    instructions = Path(__file__).parent / "CLAUDE.md"
    system = instructions.read_text(encoding="utf-8")

    # Charger les articles de la base de savoir
    try:
        articles = get_kb_articles()
    except Exception:
        articles = []

    if articles:
        system += "\n\n---\n\n## DONNEES DE REFERENCE (Base de savoir)\n\n"
        for art in articles:
            system += f"### [{art['category']}] {art['title']}\n{art['content']}\n\n"

    # Charger les produits
    try:
        products = get_products()
    except Exception:
        products = []

    if products:
        system += "\n## CATALOGUE PRODUITS\n\n"
        for p in products:
            stock = "En stock" if p.get("in_stock") else "Rupture"
            price_str = f"{p['price']:.2f} EUR" if p.get("price") else "Prix non defini"
            system += f"- **{p['name']}** (SKU: {p.get('sku') or 'N/A'}) - {price_str} - {stock}\n"
            if p.get("description"):
                system += f"  {p['description']}\n"

    # Charger la signature
    try:
        signature = get_setting("signature", "")
    except Exception:
        signature = ""

    if signature:
        system += f"\n\n## SIGNATURE EMAIL ACTUELLE\n\n{signature}"

    return system


TONE_INSTRUCTIONS = {
    "professionnel": "Ton professionnel et pose, courtois mais pas froid.",
    "chaleureux": "Ton chaleureux et empathique, montre que tu comprends vraiment le client.",
    "amical": "Ton amical et decontracte, comme un ami qui aide. Tutoiement possible.",
    "formel": "Ton tres formel et soigne, vouvoiement strict, formules de politesse elaborees.",
}

OUTPUT_RULES = """
REGLE ABSOLUE DE FORMAT DE SORTIE :
- Tu dois repondre UNIQUEMENT avec la reponse prete a etre envoyee au client.
- AUCUNE note interne, AUCUN commentaire, AUCUNE analyse, AUCUNE metadata.
- Pas de "Note:", pas de "Categorie detectee:", pas de "Langue:", pas d'emoji d'analyse.
- Pas de bloc markdown de type "> Note" ou "> Categorie".
- La reponse doit pouvoir etre copiee-collee telle quelle et envoyee directement au client.
- Si c'est un email : commence directement par "Bonjour [prenom]," (on repond a un message, pas besoin d'objet). Termine avec la signature.
- Si c'est un Instagram DM/commentaire : commence directement par le message.
- Si des informations manquent pour repondre correctement, redige quand meme une reponse
  qui demande poliment ces informations AU CLIENT (pas a l'operateur).
"""


def generate_response(customer_message, channel="email", context="", customer_name="", customer_email="", tone="professionnel"):
    """Genere une reponse SAV via l'API Claude."""
    client = anthropic.Anthropic()
    system_prompt = build_system_prompt()
    system_prompt += "\n\n" + OUTPUT_RULES

    channel_labels = {
        "email": "EMAIL",
        "instagram_dm": "INSTAGRAM DM",
        "instagram_comment": "INSTAGRAM COMMENTAIRE PUBLIC",
    }

    channel_instruction = {
        "email": "Redige la reponse EMAIL directement (on repond a un message recu, pas de ligne Objet). Commence par 'Bonjour [prenom],' et termine avec la signature.",
        "instagram_dm": "Redige le message Instagram DM directement. Court, chaleureux, 3-5 lignes max. Pas de signature.",
        "instagram_comment": "Redige le commentaire Instagram directement. 2-3 lignes max. Jamais d'infos sensibles. Redirige en DM si besoin.",
    }

    tone_desc = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professionnel"])

    parts = [f"Canal : {channel_labels.get(channel, 'EMAIL')}"]
    parts.append(f"Ton demande : {tone_desc}")
    if customer_name:
        parts.append(f"Nom du client : {customer_name}")
    if context:
        parts.append(f"Contexte : {context}")
    parts.append(f"\nMessage du client :\n---\n{customer_message}\n---")
    parts.append(f"\n{channel_instruction.get(channel, channel_instruction['email'])}")
    parts.append("\nRappel : reponds UNIQUEMENT avec le texte de la reponse, pret a copier-coller. Rien d'autre.")

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
