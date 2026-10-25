from calls_debrief.config import NOM_CANDIDAT
from calls_debrief.schemas import CompteRenduDebrief

LIMITE_TEXTE_NOTION = 2000  # caractères max par segment de texte

def _texte(contenu: str, **annotations) -> list:
    """Segments de texte Notion, découpés pour respecter la limite de 2000 caractères."""
    morceaux = [contenu[i:i + LIMITE_TEXTE_NOTION] for i in range(0, len(contenu), LIMITE_TEXTE_NOTION)] or [""]
    segments = []
    for morceau in morceaux:
        segment = {"type": "text", "text": {"content": morceau}}
        if annotations:
            segment["annotations"] = annotations
        segments.append(segment)
    return segments

def _bloc(type_bloc: str, contenu: dict) -> dict:
    return {"object": "block", "type": type_bloc, type_bloc: contenu}

def _titre(type_titre: str, contenu: str) -> dict:
    return _bloc(type_titre, {"rich_text": _texte(contenu)})

def construire_blocs(compte_rendu: CompteRenduDebrief) -> list:
    """Construit le contenu de la page Notion à partir du débrief."""
    children = []

    # 0. Contexte (date et interlocuteurs, absents des colonnes de la table)
    contexte = []
    if compte_rendu.date_estimee:
        contexte.append(f"Date : {compte_rendu.date_estimee}")
    if compte_rendu.interlocuteurs:
        contexte.append(f"Interlocuteurs : {', '.join(compte_rendu.interlocuteurs)}")
    if contexte:
        children.append(_bloc("paragraph", {"rich_text": _texte(" · ".join(contexte))}))

    # 1. Bilan global (Callout)
    children.append(_bloc("callout", {
        "rich_text": _texte(f"Bilan candidat : {compte_rendu.synthese_globale}"),
        "color": "gray_background"
    }))

    # 1b. Présentation du poste / de l'entreprise par l'interlocuteur
    if compte_rendu.informations_poste:
        children.append(_titre("heading_2", "Le poste / L'entreprise (d'après l'interlocuteur)"))
        for info in compte_rendu.informations_poste:
            children.append(_bloc("bulleted_list_item", {"rich_text": _texte(info)}))

    # 2. To-Do & Actions pour le candidat
    if compte_rendu.to_do_candidat:
        children.append(_titre("heading_2", f"Prochaines étapes (To-Do {NOM_CANDIDAT})"))
        for action in compte_rendu.to_do_candidat:
            children.append(_bloc("to_do", {"rich_text": _texte(action), "checked": False}))

    # 3. Évaluation : Points forts vs Points faibles
    children.append(_titre("heading_2", "Points forts démontrés"))
    for fort in compte_rendu.points_forts_demontres:
        children.append(_bloc("bulleted_list_item", {"rich_text": _texte(fort)}))

    children.append(_titre("heading_2", "Axes d'amélioration & Réponses à retravailler"))
    for faible in compte_rendu.axes_amelioration:
        children.append(_bloc("bulleted_list_item", {"rich_text": _texte(faible)}))

    # 4. Chronologie détaillée des questions, réponses réelles et analyse
    children.append(_titre("heading_2", f"Déroulé des questions & Verbatim de {NOM_CANDIDAT}"))
    for i, qr in enumerate(compte_rendu.chronologie_questions, 1):
        children.append(_titre("heading_3", f"Q{i} : {qr.question_posee}"))
        children.append(_bloc("paragraph", {"rich_text":
            _texte("Attente recruteur : ", bold=True, italic=True)
            + _texte(f"{qr.intention_recruteur}\n\n")
            + _texte(f"Ce que {NOM_CANDIDAT} a dit : ", bold=True)
            + _texte(f"{qr.reponse_candidat_verbatim}\n\n")
            + _texte("Diagnostic : ", bold=True, color="gray")
            + _texte(qr.analyse_reponse)
        }))
        children.append(_bloc("divider", {}))

    return children
