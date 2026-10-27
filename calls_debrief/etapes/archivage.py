import os
import shutil
from datetime import datetime

from calls_debrief.config import DOSSIER_ARCHIVES, DOSSIER_TRANSCRIPTS

def archiver(chemin: str):
    """Déplace le fichier dans les archives sans jamais écraser un fichier existant."""
    nom, ext = os.path.splitext(os.path.basename(chemin))
    destination = os.path.join(DOSSIER_ARCHIVES, nom + ext)
    if os.path.exists(destination):
        horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = os.path.join(DOSSIER_ARCHIVES, f"{nom}_{horodatage}{ext}")
    shutil.move(chemin, destination)

def sauvegarder_transcript(chemin: str, texte: str):
    """Écrit la transcription dans 03_Transcripts, sans écraser celle d'un autre fichier du même nom."""
    nom = os.path.splitext(os.path.basename(chemin))[0]
    destination = os.path.join(DOSSIER_TRANSCRIPTS, nom + ".txt")
    if os.path.exists(destination):
        with open(destination, "r", encoding="utf-8") as f:
            if f.read() == texte:  # même transcription (nouvel essai après un échec Gemini/Notion)
                return
        horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = os.path.join(DOSSIER_TRANSCRIPTS, f"{nom}_{horodatage}.txt")
    with open(destination, "w", encoding="utf-8") as f:
        f.write(texte)
