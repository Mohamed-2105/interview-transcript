"""État local du pipeline : transcriptions en cache et fichiers déjà envoyés vers Notion."""
import json
import os
from typing import Optional

from calls_debrief.config import DOSSIER_PROJET

DOSSIER_ETAT = os.path.join(DOSSIER_PROJET, ".etat")
DOSSIER_CACHE_TRANSCRIPTS = os.path.join(DOSSIER_ETAT, "transcripts")
FICHIER_ENVOYES = os.path.join(DOSSIER_ETAT, "envoyes.json")

def cle_fichier(chemin: str) -> str:
    """Identifie un fichier par son nom et sa taille (stable malgré la synchro Google Drive)."""
    return f"{os.path.basename(chemin)}|{os.path.getsize(chemin)}"

# --- Cache des transcriptions (évite de relancer Whisper après un échec Gemini/Notion) ---
def _chemin_cache(cle: str) -> str:
    return os.path.join(DOSSIER_CACHE_TRANSCRIPTS, cle.replace("|", "_").replace(os.sep, "_") + ".txt")

def lire_transcript_cache(cle: str) -> Optional[str]:
    try:
        with open(_chemin_cache(cle), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None

def ecrire_transcript_cache(cle: str, texte: str):
    os.makedirs(DOSSIER_CACHE_TRANSCRIPTS, exist_ok=True)
    with open(_chemin_cache(cle), "w", encoding="utf-8") as f:
        f.write(texte)

def supprimer_transcript_cache(cle: str):
    try:
        os.remove(_chemin_cache(cle))
    except FileNotFoundError:
        pass

# --- Registre des envois Notion (évite un doublon si l'archivage échoue) ---
def _lire_envoyes() -> dict:
    try:
        with open(FICHIER_ENVOYES, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _ecrire_envoyes(envoyes: dict):
    os.makedirs(DOSSIER_ETAT, exist_ok=True)
    with open(FICHIER_ENVOYES, "w", encoding="utf-8") as f:
        json.dump(envoyes, f, ensure_ascii=False, indent=2)

def url_deja_envoye(cle: str) -> Optional[str]:
    return _lire_envoyes().get(cle)

def marquer_envoye(cle: str, url: Optional[str]):
    envoyes = _lire_envoyes()
    envoyes[cle] = url or ""
    _ecrire_envoyes(envoyes)

def oublier_envoi(cle: str):
    envoyes = _lire_envoyes()
    if envoyes.pop(cle, None) is not None:
        _ecrire_envoyes(envoyes)
