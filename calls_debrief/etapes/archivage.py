import os
import shutil
from datetime import datetime

from calls_debrief.config import DOSSIER_ARCHIVES

def archiver(chemin: str):
    """Déplace le fichier dans les archives sans jamais écraser un fichier existant."""
    nom, ext = os.path.splitext(os.path.basename(chemin))
    destination = os.path.join(DOSSIER_ARCHIVES, nom + ext)
    if os.path.exists(destination):
        horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = os.path.join(DOSSIER_ARCHIVES, f"{nom}_{horodatage}{ext}")
    shutil.move(chemin, destination)
