"""SAV Assistant CibleSkin - Moteur IA avec l'API Claude."""

import os
from pathlib import Path

import anthropic

DATA_DIR = Path(__file__).parent / "data"
DRAFTS_DIR = Path(__file__).parent / "drafts"


def load_reference_data() -> str:
    """Charge tous les fichiers de reference du dossier /data/."""
    parts = []
    if not DATA_DIR.exists():
        return ""

    for filepath in sorted(DATA_DIR.iterdir()):
        if filepath.name.startswith("."):
            continue
        if filepath.suffix in (".txt", ".md", ".csv"):
            try:
                content = filepath.read_text(encoding="utf-8")
                parts.append(f"--- {filepath.name} ---\n{content}")
            except Exception:
                parts.append(f"--- {filepath.name} --- (erreur de lecture)")

    return "\n\n".join(parts)


def load_signature() -> str:
    """Charge la signature email depuis /data/signature.txt."""
    sig_path = DATA_DIR / "signature.txt"
    if sig_path.exists():
        return sig_path.read_text(encoding="utf-8").strip()
    return ""


def build_system_prompt() -> str:
    """Construit le system prompt avec les donnees de reference."""
    instructions = Path(__file__).parent / "CLAUDE.md"
    system = instructions.read_text(encoding="utf-8")

    ref_data = load_reference_data()
    signature = load_signature()

    system += "\n\n---\n\n## DONNEES DE REFERENCE CHARGEES\n\n"
    if ref_data:
        system += ref_data
    else:
        system += "(Aucun fichier de reference trouve dans /data/)"

    system += f"\n\n## SIGNATURE EMAIL ACTUELLE\n\n{signature}"

    return system


def generate_response(
    customer_message: str,
    channel: str = "email",
    context: str = "",
) -> str:
    """Genere une reponse SAV via l'API Claude.

    Args:
        customer_message: Le message du client.
        channel: "email", "instagram_dm" ou "instagram_comment".
        context: Contexte supplementaire (historique, infos commande...).

    Returns:
        La reponse generee par Claude.
    """
    client = anthropic.Anthropic()
    system_prompt = build_system_prompt()

    channel_instruction = {
        "email": "Genere une reponse EMAIL complete avec objet. Utilise la signature.",
        "instagram_dm": "Genere une reponse Instagram DM (courte, chaleureuse, 3-5 lignes).",
        "instagram_comment": (
            "Genere une reponse Instagram COMMENTAIRE PUBLIC "
            "(2-3 lignes, ne jamais partager d'infos sensibles, "
            "rediriger en DM si necessaire)."
        ),
    }

    context_line = f"Contexte supplementaire : {context}\n" if context else ""
    user_content = (
        f"Canal : {channel.upper()}\n\n"
        f"{context_line}\n"
        f"Message client :\n"
        f"---\n{customer_message}\n---"
    )

    instruction = channel_instruction.get(channel, channel_instruction["email"])
    user_content += f"\n\nInstruction : {instruction}"

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


def save_draft(response_text: str, channel: str, customer_message: str) -> Path:
    """Sauvegarde un brouillon de reponse dans /drafts/."""
    DRAFTS_DIR.mkdir(exist_ok=True)
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{channel}_{timestamp}.txt"
    filepath = DRAFTS_DIR / filename

    content = f"Canal: {channel}\n"
    content += f"Date: {datetime.now().isoformat()}\n"
    content += f"Message client:\n{customer_message}\n"
    content += f"\n{'=' * 50}\nReponse generee:\n{'=' * 50}\n\n"
    content += response_text

    filepath.write_text(content, encoding="utf-8")
    return filepath
