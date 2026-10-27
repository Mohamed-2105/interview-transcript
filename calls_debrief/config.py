import os
from dotenv import load_dotenv

# Racine du projet (dossier parent du paquet) : .env, .etat/ et .calls_database_id y vivent
DOSSIER_PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(DOSSIER_PROJET, ".env"))

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Token Hugging Face (modèle pyannote à accès restreint) ; sans lui, transcription sans locuteurs
HF_TOKEN = os.getenv("HF_TOKEN")
# Prénom de la personne interviewée : sert à l'identifier dans la transcription et à personnaliser le débrief
NOM_CANDIDAT = os.getenv("CANDIDATE_NAME", "").strip()
# Base ou page Notion où créer les débriefs (ID ou lien) ; à défaut, l'ID enregistré dans .calls_database_id
NOTION_CIBLE = os.getenv("NOTION_TARGET")
FICHIER_CIBLE_HERITE = os.path.join(DOSSIER_PROJET, ".calls_database_id")

# Dossier de travail (ex. un dossier Google Drive synchronisé) contenant 01_A_Traiter et 02_Archives
BASE_DRIVE = os.path.expanduser(os.getenv("CALLS_FOLDER", "~/assistant-calls"))
DOSSIER_A_TRAITER = os.path.join(BASE_DRIVE, "01_A_Traiter")
DOSSIER_ARCHIVES = os.path.join(BASE_DRIVE, "02_Archives")
# Transcriptions telles qu'envoyées à Gemini (avec locuteurs si la diarisation a tourné)
DOSSIER_TRANSCRIPTS = os.path.join(BASE_DRIVE, "03_Transcripts")

EXTENSIONS_AUDIO = ('.m4a', '.mp3', '.wav')
EXTENSIONS_TEXTE = ('.txt', '.vtt', '.srt')

MODELE_WHISPER = "mlx-community/whisper-large-v3-turbo"
MODELE_DIARISATION = "pyannote/speaker-diarization-community-1"
MODELES_GEMINI = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
