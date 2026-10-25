"""Cible Notion (base ou simple page) : détection du type et adaptation aux colonnes existantes."""
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import httpx

from calls_debrief.config import NOTION_TOKEN, NOTION_CIBLE, FICHIER_CIBLE_HERITE
from calls_debrief.notion.blocs import LIMITE_TEXTE_NOTION

NOTION_API = "https://api.notion.com/v1"

# Colonnes reconnues dans une base : noms acceptés (comparés sans casse, accents ni espaces spéciaux) et types acceptés
COLONNES_CONNUES = {
    "espace": (["espace"], ["select"]),
    "categorie": (["categorie", "category"], ["select"]),
    "date": (["date", "date de l'entretien", "date entretien", "interview date"], ["date"]),
    "interlocuteurs": (["interlocuteurs", "recruteurs", "interviewers"], ["multi_select", "rich_text"]),
}

def get_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

def normaliser_nom(nom: str) -> str:
    """'Catégorie', 'categorie ' et 'Relue ?' / 'relue ?' deviennent comparables."""
    nom = unicodedata.normalize("NFKD", nom)  # sépare les accents et transforme les espaces insécables
    nom = "".join(c for c in nom if not unicodedata.combining(c))
    return " ".join(nom.casefold().split())

def extraire_id(valeur: str) -> Optional[str]:
    """Accepte un ID brut ou un lien Notion (le dernier identifiant du lien est retenu)."""
    ids = re.findall(r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}", valeur.split("?")[0].lower())
    return ids[-1].replace("-", "") if ids else None

@dataclass
class CibleNotion:
    id: str
    est_base: bool
    colonnes: dict = field(default_factory=dict)  # nom réel -> définition Notion (vide pour une page)

    def colonne(self, champ: str) -> Optional[str]:
        """Nom réel de la colonne correspondant au champ, ou None si la base ne l'a pas."""
        noms, types = COLONNES_CONNUES[champ]
        for nom_reel, definition in self.colonnes.items():
            if normaliser_nom(nom_reel) in noms and definition["type"] in types:
                return nom_reel
        return None

    def colonne_titre(self) -> str:
        if not self.est_base:
            return "title"
        return next(nom for nom, definition in self.colonnes.items() if definition["type"] == "title")

    def options_espace(self) -> Optional[List[str]]:
        """Options de la colonne Espace, que Gemini devra choisir ; None si la colonne n'existe pas."""
        nom = self.colonne("espace")
        if not nom:
            return None
        return [option["name"] for option in self.colonnes[nom]["select"]["options"]] or None

def _lire_id_cible() -> str:
    valeur = NOTION_CIBLE
    if not valeur and os.path.exists(FICHIER_CIBLE_HERITE):
        with open(FICHIER_CIBLE_HERITE, "r") as f:
            valeur = f.read().strip()
    if not valeur:
        raise RuntimeError("Aucune cible Notion : définis NOTION_TARGET dans .env (ID ou lien d'une page ou d'une base).")

    cible_id = extraire_id(valeur)
    if not cible_id:
        raise RuntimeError(f"NOTION_TARGET ne contient pas d'ID Notion reconnaissable : {valeur!r}")
    return cible_id

def charger_cible() -> CibleNotion:
    cible_id = _lire_id_cible()
    headers = get_headers()

    r = httpx.get(f"{NOTION_API}/databases/{cible_id}", headers=headers, timeout=20.0)
    if r.status_code == 200:
        base = r.json()
        cible = CibleNotion(cible_id, est_base=True, colonnes=base["properties"])
        titre = "".join(t["plain_text"] for t in base.get("title", [])) or cible_id
        reconnues = {champ: cible.colonne(champ) for champ in COLONNES_CONNUES}
        print(f"Cible Notion : base « {titre} »")
        print(f"  Colonnes remplies : {cible.colonne_titre()} (titre), " + ", ".join(nom for nom in reconnues.values() if nom))
        absentes = [champ for champ, nom in reconnues.items() if not nom]
        if absentes:
            print(f"  Non trouvées dans la base (ignorées) : {', '.join(absentes)}")
        return cible

    r_page = httpx.get(f"{NOTION_API}/pages/{cible_id}", headers=headers, timeout=20.0)
    if r_page.status_code == 200:
        print("Cible Notion : page simple (les débriefs seront créés en sous-pages)")
        return CibleNotion(cible_id, est_base=False)

    raise RuntimeError(
        f"Cible Notion {cible_id} inaccessible : vérifie l'ID et que la page ou la base est partagée avec l'intégration "
        f"({r_page.status_code} : {r_page.text})"
    )

def _valeur_notion(type_colonne: str, valeur):
    if type_colonne == "select":
        return {"select": {"name": valeur}}
    if type_colonne == "date":
        return {"date": {"start": valeur}}
    if type_colonne == "multi_select":
        # Notion refuse les virgules dans une option de multi-select
        return {"multi_select": [{"name": v.replace(",", " -")[:100]} for v in valeur]}
    if type_colonne == "rich_text":
        return {"rich_text": [{"text": {"content": ", ".join(valeur)[:LIMITE_TEXTE_NOTION]}}]}
    raise ValueError(f"Type de colonne non géré : {type_colonne}")

def _date_valide(date: Optional[str]) -> Optional[str]:
    try:
        datetime.strptime(date or "", "%Y-%m-%d")
        return date
    except ValueError:
        return None

def construire_proprietes(cible: CibleNotion, compte_rendu) -> dict:
    """Propriétés de la page, limitées aux colonnes qui existent réellement dans la cible."""
    titre = {"title": [{"text": {"content": compte_rendu.titre_entretien[:LIMITE_TEXTE_NOTION]}}]}
    proprietes = {cible.colonne_titre(): titre}
    if not cible.est_base:
        return proprietes

    valeurs = {
        "espace": getattr(compte_rendu, "espace", None),
        "categorie": "Interview",  # le pipeline ne traite que des entretiens
        "date": _date_valide(compte_rendu.date_estimee),
        "interlocuteurs": compte_rendu.interlocuteurs,
    }
    for champ, valeur in valeurs.items():
        nom = cible.colonne(champ)
        if nom and valeur:
            proprietes[nom] = _valeur_notion(cible.colonnes[nom]["type"], valeur)
    return proprietes
