import re
from typing import Optional

from calls_debrief import etat
from calls_debrief.config import EXTENSIONS_AUDIO, MODELE_WHISPER

# Chargement de FFmpeg pour la lecture des audios
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

try:
    import mlx_whisper
except ImportError:
    mlx_whisper = None

def obtenir_transcript(chemin: str, cle: str) -> Optional[str]:
    """Retourne le texte du fichier (transcrit si audio), ou None s'il ne peut pas être traité."""
    if chemin.lower().endswith(EXTENSIONS_AUDIO):
        texte = etat.lire_transcript_cache(cle)
        if texte is not None:
            print("Transcription récupérée depuis le cache.")
            return texte
        if not mlx_whisper:
            print("mlx_whisper non disponible, fichier ignoré.")
            return None
        print("Transcription locale via mlx-whisper (Apple Silicon)...")
        res = mlx_whisper.transcribe(chemin, path_or_hf_repo=MODELE_WHISPER)
        texte = res.get("text", "")
        etat.ecrire_transcript_cache(cle, texte)
        return texte

    with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
        texte = f.read()
    if chemin.lower().endswith(('.vtt', '.srt')):
        return nettoyer_sous_titres(texte)
    return texte

def nettoyer_sous_titres(texte: str) -> str:
    """Retire numéros, horodatages et balises d'un .vtt/.srt pour ne garder que les répliques."""
    lignes = []
    dans_note = False
    for ligne in texte.splitlines():
        ligne = ligne.strip().lstrip("﻿")
        if not ligne:
            dans_note = False
            continue
        if dans_note:
            continue
        if ligne.startswith(("NOTE", "STYLE", "REGION")):  # blocs non parlés, jusqu'à la ligne vide
            dans_note = True
            continue
        if ligne.startswith("WEBVTT") or "-->" in ligne or ligne.isdigit():
            continue
        ligne = re.sub(r"<v(?:\.[^ >]*)?\s+([^>]+)>", r"\1 : ", ligne)  # <v Nom> -> "Nom : "
        ligne = re.sub(r"<[^>]+>", "", ligne).strip()                   # autres balises (<c>, <i>, horodatages…)
        if ligne and (not lignes or lignes[-1] != ligne):              # doublons des sous-titres auto
            lignes.append(ligne)
    return "\n".join(lignes)
