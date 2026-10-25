from pydantic import BaseModel, Field, create_model
from typing import List, Optional, Literal

from calls_debrief.config import NOM_CANDIDAT

# --- SCHÉMAS STRUCTURÉS : COACHING & DÉBRIEF CANDIDAT ---
class EchangeQuestionReponse(BaseModel):
    question_posee: str = Field(description="Question telle que l'interlocuteur l'a réellement posée, dans ses propres termes et dans sa langue d'origine (sans les tics de langage). Ne la reformule pas.")
    intention_recruteur: str = Field(description="Attente précise du recruteur : ce qu'il évalue concrètement à cet instant.")
    reponse_candidat_verbatim: str = Field(
        description=f"Transcription fidèle de ce que {NOM_CANDIDAT} a RÉELLEMENT dit. Conserve ses mots, son vocabulaire, son niveau de précision et sa structure de phrase exacte. Retire UNIQUEMENT les tics de langage ('euh', 'hum', faux départs). Ne réécris pas dans un style formel ou artificiel."
    )
    analyse_reponse: str = Field(
        description="Analyse neutre et sans complaisance : la réponse répond-elle à la question ? Est-elle trop longue, trop floue, percutante ou hors-sujet ?"
    )

class CompteRenduDebrief(BaseModel):
    titre_entretien: str = Field(description="Titre clair et contextualisé (ex: 'Entretien [Poste] - [Entreprise]').")
    date_estimee: Optional[str] = Field(description="Date au format YYYY-MM-DD si déduite ou mentionnée.")
    interlocuteurs: List[str] = Field(description=f"Noms et rôles/entreprises des interlocuteurs en face de {NOM_CANDIDAT}.")
    informations_poste: List[str] = Field(
        description="Tout ce que l'interlocuteur a expliqué sur le poste, l'équipe, l'entreprise, le secteur, les outils, le profil recherché, le process de recrutement, les prochaines étapes, la rémunération ou les conditions. Une puce par information, dans l'ordre où elle a été donnée, en reprenant fidèlement ses termes, chiffres, noms et exemples, dans sa langue d'origine. Ne résume pas, ne généralise pas, n'ajoute rien qui n'a pas été dit. Liste vide si l'interlocuteur n'a rien présenté."
    )
    synthese_globale: str = Field(description=f"Bilan global de l'échange en 2 à 4 phrases du point de vue de la performance de {NOM_CANDIDAT}.")
    chronologie_questions: List[EchangeQuestionReponse] = Field(description=f"Déroulé séquentiel des questions posées par le recruteur et réponses épurées de {NOM_CANDIDAT}.")
    points_forts_demontres: List[str] = Field(description="Ce qui a particulièrement bien fonctionné : clarté technique, arguments percutants, aisance, bonne valorisation des expériences.")
    axes_amelioration: List[str] = Field(description="Points faibles ou axes de progrès : réponses trop longues, hésitations techniques, manque de précision, questions pièges mal esquivées.")
    to_do_candidat: List[str] = Field(description=f"Plan d'action exclusif pour {NOM_CANDIDAT} : relances, notions techniques à réviser, documents ou portfolio à envoyer.")

def schema_debrief(options_espace: Optional[List[str]] = None) -> type:
    """Schéma envoyé à Gemini : ajoute le champ 'espace' limité aux options de la colonne Notion, si elle existe."""
    if not options_espace:
        return CompteRenduDebrief
    return create_model(
        "CompteRenduDebriefAvecEspace",
        __base__=CompteRenduDebrief,
        espace=(Literal[tuple(options_espace)], Field(description=f"Option qui correspond le mieux à l'entretien, parmi : {', '.join(options_espace)}.")),
    )
