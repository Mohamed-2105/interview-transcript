import re
from typing import Optional

from calls_debrief import etat
from calls_debrief.config import EXTENSIONS_AUDIO, HF_TOKEN, MODELE_DIARISATION, MODELE_WHISPER

# Chargement de FFmpeg pour la lecture des audios
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

try:
    import mlx_whisper
    from mlx_whisper.audio import SAMPLE_RATE, load_audio
except ImportError:
    mlx_whisper = None

try:
    import torch
    from pyannote.audio import Pipeline
except ImportError:
    Pipeline = None

def diariser(audio) -> list:
    """Tours de parole pyannote [(début, fin, locuteur)], ou [] si la diarisation est indisponible."""
    if Pipeline is None or not HF_TOKEN:
        print("pyannote ou HF_TOKEN absent : transcription sans locuteurs.")
        return []
    pipeline = Pipeline.from_pretrained(MODELE_DIARISATION, token=HF_TOKEN)
    if torch.backends.mps.is_available():
        pipeline.to(torch.device("mps"))
    sortie = pipeline({"waveform": torch.from_numpy(audio)[None], "sample_rate": SAMPLE_RATE})
    # pyannote 4 : la version "exclusive" (un seul locuteur à la fois) s'aligne mieux sur Whisper
    annotation = getattr(sortie, "exclusive_speaker_diarization", sortie)
    return [(tour.start, tour.end, loc) for tour, _, loc in annotation.itertracks(yield_label=True)]

def fusionner(segments: list, tours: list) -> str:
    """Attribue à chaque segment Whisper le locuteur qui le recouvre le plus, et regroupe les répliques."""
    lignes, precedent = [], None
    for seg in segments:
        recouvrements = {}
        for debut, fin, loc in tours:
            r = min(seg["end"], fin) - max(seg["start"], debut)
            if r > 0:
                recouvrements[loc] = recouvrements.get(loc, 0) + r
        # Sans recouvrement (silence mal découpé), on garde le locuteur précédent
        loc = max(recouvrements, key=recouvrements.get) if recouvrements else precedent or "INCONNU"
        texte = seg["text"].strip()
        if not texte:
            continue
        if loc == precedent:
            lignes[-1] += " " + texte
        else:
            lignes.append(f"{loc} : {texte}")
            precedent = loc
    return "\n".join(lignes)

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
        audio = load_audio(chemin)  # décodé une seule fois, partagé par Whisper et pyannote
        res = mlx_whisper.transcribe(audio, path_or_hf_repo=MODELE_WHISPER)
        print("Identification des locuteurs via pyannote...")
        tours = diariser(audio)
        texte = fusionner(res["segments"], tours) if tours else res.get("text", "")
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
