#!/usr/bin/env python3
"""SAV Assistant CibleSkin - Interface ligne de commande."""

import sys

from dotenv import load_dotenv

from sav_assistant import generate_response, load_signature, save_draft

load_dotenv()

CHANNELS = {"1": "email", "2": "instagram_dm", "3": "instagram_comment"}


def main():
    print("=" * 50)
    print("  SAV Assistant - CibleSkin")
    print("=" * 50)

    sig = load_signature()
    if sig:
        print(f"\nSignature chargee : {sig.splitlines()[0]}...")

    while True:
        print("\n--- Nouveau message ---")
        print("Canal : [1] Email  [2] Insta DM  [3] Insta Commentaire  [q] Quitter")
        choice = input("> ").strip().lower()

        if choice == "q":
            print("Au revoir !")
            break

        channel = CHANNELS.get(choice)
        if not channel:
            print("Choix invalide.")
            continue

        print(f"\nCanal: {channel.upper()}")
        print("Contexte (optionnel, appuyez sur Entree pour passer) :")
        context = input("> ").strip()

        print("Message client (terminez par une ligne vide) :")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)

        customer_message = "\n".join(lines)
        if not customer_message:
            print("Message vide, annule.")
            continue

        print("\nGeneration en cours...")
        try:
            response = generate_response(customer_message, channel, context)
            print("\n" + "=" * 50)
            print("REPONSE GENEREE")
            print("=" * 50)
            print(response)
            print("=" * 50)

            draft = save_draft(response, channel, customer_message)
            print(f"\nBrouillon sauvegarde : {draft}")
        except Exception as e:
            print(f"\nErreur : {e}")


if __name__ == "__main__":
    main()
