"""Les quatre fichiers publics du dépôt, téléchargés par script et jamais commités.

Trois viennent du BSIF et de la Banque du Canada, le quatrième est le rapport de 2022 qui porte les
chiffres à retrouver. Aucun n'est redistribué ici. Les conditions des deux organismes autorisent
l'usage et la copie avec attribution, mais la convention du portefeuille est de ne rien commiter.
Cette convention évite d'avoir à trancher la question à chaque fichier.

Une adresse a été corrigée le 2026-08-30. Le rapport n'est pas sous `/uploads/2022/01/`, chemin qui
répond 404, mais sous `/uploads/2021/11/`, alors même que le rapport porte la date de janvier 2022.
"""

from __future__ import annotations

import ssl
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RACINE = Path("data/raw")

# Une identification est exigée par plusieurs sites de données publiques, et c'est de toute façon la
# politesse minimale envers un serveur public.
AGENT = "Guillaume Vaudescal 88989051+Guilou001@users.noreply.github.com"


@dataclass(frozen=True)
class Fichier:
    """Un fichier public : son nom local, son adresse, ce qu'il contient et sous quelle licence."""

    nom: str
    url: str
    contenu: str
    licence: str


FICHIERS = [
    Fichier("scse_instructions.xlsx",
            "https://www.osfi-bsif.gc.ca/sites/default/files/documents/"
            "scse-instructions-enasc-en_2.xlsx",
            "les instructions de l'exercice normalisé, dont l'onglet « Credit Risk Example » qui "
            "porte l'exemple travaillé complet",
            "Bureau du surintendant des institutions financières, usage permis avec attribution"),
    Fichier("scse_classeur.xlsx",
            "https://www.osfi-bsif.gc.ca/sites/default/files/documents/"
            "scse-workbook-classeur-enasc-en_0.xlsx",
            "le classeur que chaque institution remplit, treize feuilles dont « Credit Risk »",
            "Bureau du surintendant des institutions financières, usage permis avec attribution"),
    Fichier("scenarios_bdc.csv",
            "https://www.bankofcanada.ca/wp-content/uploads/2022/01/"
            "climate-transition-scenario-data.csv",
            "les trajectoires du projet pilote : 59 584 observations, 9 géographies, 4 scénarios, "
            "15 secteurs, 66 variables, 2020 à 2050",
            "Banque du Canada, usage et redistribution permis avec attribution"),
    Fichier("rapport_pilote.pdf",
            "https://www.bankofcanada.ca/wp-content/uploads/2021/11/"
            "BoC-OSFI-Using-Scenario-Analysis-to-Assess-Climate-Transition-Risk.pdf",
            "le rapport du projet pilote de 2022, 62 pages, dont le graphique 16 en page 32 du "
            "PDF, folio imprimé 31",
            "Banque du Canada et BSIF, usage permis avec attribution"),
]


def _contexte() -> ssl.SSLContext:
    """Le contexte TLS, adossé au magasin de certificats du système quand c'est possible.

    Sur macOS, la bibliothèque standard de Python ne lit pas le trousseau du système. Les serveurs
    du BSIF et de la Banque du Canada répondent alors « unable to get local issuer certificate »,
    alors que `curl` passe sur la même machine. `truststore` branche le magasin du système, ce qui
    règle le cas sans désactiver aucune vérification.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:      # pragma: no cover - dépend de l'environnement
        return ssl.create_default_context()


def telecharger(fichier: Fichier, racine: Path = RACINE) -> Path:
    """Un fichier, écrit tel quel sur le disque."""
    racine.mkdir(parents=True, exist_ok=True)
    chemin = racine / fichier.nom
    requete = urllib.request.Request(fichier.url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(requete, timeout=180, context=_contexte()) as reponse:  # noqa: S310
        chemin.write_bytes(reponse.read())
    return chemin


def fetch(racine: Path = RACINE) -> dict[str, int]:
    """Les quatre fichiers, et la taille de chacun en octets."""
    return {f.nom: telecharger(f, racine).stat().st_size for f in FICHIERS}


def chemin(nom: str, racine: Path = RACINE) -> Path:
    """Le chemin local d'un fichier, avec un message utile s'il manque."""
    cible = racine / nom
    if not cible.exists():
        raise FileNotFoundError(f"{cible} absent : lancer d'abord `scc fetch`")
    return cible
