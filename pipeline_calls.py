import os
import traceback

from calls_debrief import etat
from calls_debrief.config import DOSSIER_A_TRAITER, DOSSIER_ARCHIVES, DOSSIER_TRANSCRIPTS, EXTENSIONS_AUDIO, EXTENSIONS_TEXTE, NOM_CANDIDAT
from calls_debrief.etat import cle_fichier
from calls_debrief.etapes.transcription import obtenir_transcript
from calls_debrief.etapes.analyse import analyser_transcript
from calls_debrief.etapes.archivage import archiver, sauvegarder_transcript
from calls_debrief.notion.cible import CibleNotion, charger_cible
from calls_debrief.notion.export import envoyer_debrief_vers_notion

def traiter_fichier(chemin: str, cible: CibleNotion):
    cle = cle_fichier(chemin)

    url_existante = etat.url_deja_envoye(cle)
    if url_existante is not None:
        # Page déjà créée lors d'un passage précédent dont l'archivage avait échoué
        print(f"Déjà envoyé vers Notion ({url_existante or 'URL inconnue'}), archivage uniquement.")
    else:
        # 1. Transcription / lecture
        texte_transcript = obtenir_transcript(chemin, cle)
        if texte_transcript is None:
            return
        if not texte_transcript.strip():
            print("Fichier vide ou inexploitable. Ignoré.")
            return
        sauvegarder_transcript(chemin, texte_transcript)

        # 2. Analyse
        print("Analyse candidat & Débrief en cours par Gemini...")
        compte_rendu = analyser_transcript(texte_transcript, cible.options_espace())

        # 3. Export Notion
        print("Envoi vers Notion...")
        url = envoyer_debrief_vers_notion(compte_rendu, cible)
        etat.marquer_envoye(cle, url)
        etat.supprimer_transcript_cache(cle)

    # 4. Archivage
    archiver(chemin)
    etat.oublier_envoi(cle)
    print(f"Fichier {os.path.basename(chemin)} archivé avec succès.")

def lancer_pipeline_calls():
    if not NOM_CANDIDAT:
        raise SystemExit("CANDIDATE_NAME manquant dans .env : indique le prénom de la personne interviewée (ex. CANDIDATE_NAME=Alex).")

    os.makedirs(DOSSIER_A_TRAITER, exist_ok=True)
    os.makedirs(DOSSIER_ARCHIVES, exist_ok=True)
    os.makedirs(DOSSIER_TRANSCRIPTS, exist_ok=True)

    cible = charger_cible()

    fichiers = [f for f in os.listdir(DOSSIER_A_TRAITER) if f.lower().endswith(EXTENSIONS_AUDIO + EXTENSIONS_TEXTE)]
    print(f"Fichiers à traiter : {fichiers}")

    echecs = []
    for fichier in fichiers:
        print(f"\nTraitement : {fichier}")
        try:
            traiter_fichier(os.path.join(DOSSIER_A_TRAITER, fichier), cible)
        except Exception:
            print(f"[ÉCHEC] {fichier} laissé dans {DOSSIER_A_TRAITER} :")
            traceback.print_exc()
            echecs.append(fichier)

    if echecs:
        print(f"\n{len(echecs)} fichier(s) en échec : {echecs}")

if __name__ == "__main__":
    lancer_pipeline_calls()
