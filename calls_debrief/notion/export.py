from typing import Optional
import httpx

from calls_debrief.schemas import CompteRenduDebrief
from calls_debrief.notion.blocs import construire_blocs
from calls_debrief.notion.cible import CibleNotion, NOTION_API, get_headers, construire_proprietes

def envoyer_debrief_vers_notion(compte_rendu: CompteRenduDebrief, cible: CibleNotion) -> Optional[str]:
    """Crée la page Notion du débrief (ligne de la base ou sous-page) et retourne son URL."""
    headers = get_headers()
    children = construire_blocs(compte_rendu)
    proprietes = construire_proprietes(cible, compte_rendu)

    payload = {
        "parent": {"database_id": cible.id} if cible.est_base else {"page_id": cible.id},
        "properties": proprietes,
        "children": children[:100]
    }

    r = httpx.post(f"{NOTION_API}/pages", headers=headers, json=payload, timeout=30.0)
    if r.status_code != 200 and len(proprietes) > 1:
        print(f"\n[AVERTISSEMENT NOTION] Propriétés rejetées ({r.status_code}) : {r.text}\nNouvel essai avec le titre seul...")
        colonne_titre = cible.colonne_titre()
        payload["properties"] = {colonne_titre: proprietes[colonne_titre]}
        r = httpx.post(f"{NOTION_API}/pages", headers=headers, json=payload, timeout=30.0)

    if r.status_code != 200:
        print(f"\n[ERREUR NOTION] Statut {r.status_code} : {r.text}")
        raise RuntimeError(f"Échec création page Notion : {r.text}")

    nouvelle_page = r.json()
    page_id = nouvelle_page.get("id")

    # Pagination Notion si plus de 100 blocs
    if page_id and len(children) > 100:
        for i in range(100, len(children), 100):
            r = httpx.patch(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=headers,
                json={"children": children[i:i+100]},
                timeout=30.0
            )
            if r.status_code != 200:
                # La page existe déjà : on prévient sans lever d'erreur pour éviter un doublon au prochain passage
                print(f"\n[AVERTISSEMENT NOTION] Blocs {i}-{min(i + 100, len(children))} non ajoutés à {nouvelle_page.get('url')} ({r.status_code}) : {r.text}")
                break

    espace = getattr(compte_rendu, "espace", None)
    print(f"Fiche enregistrée : {compte_rendu.titre_entretien}{f' [{espace}]' if espace else ''} -> {nouvelle_page.get('url')}")
    return nouvelle_page.get("url")
