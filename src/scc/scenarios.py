"""Le fichier de scénarios de la Banque du Canada, et le seul maillon qu'il permet de refaire.

En 2022 la Banque du Canada et le BSIF ont publié le rapport d'un projet pilote mené avec six
institutions financières, et le fichier de trajectoires qui le nourrit. Le rapport annonce, page 32,
que le secteur des produits pétroliers raffinés voit sa probabilité de défaut monter de 450 % d'ici
2050 pour une baisse de 72 % de son résultat net, et le secteur des cultures de 141 % pour une baisse
de 32 %.

Ce module refait le premier maillon, celui du résultat net, qui se déduit entièrement du fichier
public. Il ne refait pas le second, et c'est important : le rapport dit page 30 que les points de
calibration viennent d'évaluations d'emprunteurs faites par les six institutions sur leurs propres
dossiers, puis ajustées à dire d'expert, avant d'être résumées par un modèle de type Merton. Ces
évaluations ne sont pas publiques. Le second maillon est donc **non reconstructible**, et le dépôt
l'écrit plutôt que de fabriquer un chiffre qui y ressemblerait.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

URL = "https://www.bankofcanada.ca/wp-content/uploads/2022/01/climate-transition-scenario-data.csv"
RAPPORT = ("https://www.bankofcanada.ca/wp-content/uploads/2021/11/"
           "BoC-OSFI-Using-Scenario-Analysis-to-Assess-Climate-Transition-Risk.pdf")

REFERENCE = "Baseline (2019 policies)"
POSTES = ("Revenue", "Direct emissions costs", "Indirect costs")

# Ce que le rapport annonce, page 32, pour le Canada en 2050 sous « Below 2°C immediate ».
PUBLIES = {
    "Refined oil products": {"resultat_net_pct": -72.0, "pd_pct": 450.0},
    "Crops": {"resultat_net_pct": -32.0, "pd_pct": 141.0},
}

FRANCAIS = {
    "Crops": "Cultures", "Livestock": "Élevage", "Forestry": "Foresterie", "Coal": "Charbon",
    "Oil & Gas": "Pétrole et gaz", "Oil": "Pétrole", "Gas": "Gaz",
    "Refined oil products": "Produits pétroliers raffinés",
    "Energy-intensive industries": "Industries à forte intensité énergétique",
    "Commercial transportation": "Transport commercial", "Electricity": "Électricité",
    "Other": "Autres", "National": "Ensemble de l'économie",
}


def charger(chemin: Path | str) -> pd.DataFrame:
    """Le fichier tel qu'il est servi : un en-tête de conditions, puis les observations.

    Le fichier commence par un bloc de métadonnées et la table ne débute qu'après la ligne
    « OBSERVATIONS ». La chercher plutôt que compter les lignes évite qu'une mise à jour du bloc
    d'en-tête décale tout en silence.
    """
    texte = Path(chemin).read_text(encoding="utf-8-sig")
    lignes = texte.splitlines()
    debut = next(i for i, ligne in enumerate(lignes) if ligne.strip().strip('"') == "OBSERVATIONS")
    table = pd.read_csv(io.StringIO("\n".join(lignes[debut + 1:])))
    table["CL_YEAR"] = table["CL_YEAR"].astype(int)
    return table


def resultat_net(table: pd.DataFrame, geographie: str = "Canada", annee: int = 2050) -> pd.DataFrame:
    """Le résultat net par secteur et par scénario : produits, moins les deux postes de coûts.

    Le rapport ne publie pas de ligne « résultat net ». Il publie les produits, les coûts directs
    d'émission et les coûts indirects, tous trois en dizaines de milliards de dollars de 2014, et la
    soustraction est celle que le rapport décrit au chapitre du risque de crédit.
    """
    bloc = table[table.CL_GEOGRAPHY.eq(geographie) & table.CL_YEAR.eq(annee)
                 & table.CL_VARIABLE.isin(POSTES)]
    large = bloc.pivot_table(index=["CL_SECTOR", "CL_SCENARIO"], columns="CL_VARIABLE",
                             values="CL_VALUE")
    complets = large.dropna(subset=list(POSTES))
    complets = complets.assign(
        resultat_net=complets["Revenue"] - complets["Direct emissions costs"]
        - complets["Indirect costs"])
    return complets


def variation(table: pd.DataFrame, geographie: str = "Canada", annee: int = 2050,
              scenario: str = "Below 2°C immediate") -> pd.DataFrame:
    """La variation du résultat net contre le scénario de référence, en pourcentage.

    C'est l'axe horizontal du graphique 16 du rapport, celui que le dépôt cherche à retrouver.
    """
    net = resultat_net(table, geographie, annee)["resultat_net"].unstack("CL_SCENARIO")
    if scenario not in net.columns or REFERENCE not in net.columns:
        raise ValueError(f"scénario absent du fichier : {scenario}")
    lignes = pd.DataFrame({
        "secteur": [FRANCAIS.get(s, s) for s in net.index],
        "reference": net[REFERENCE].to_numpy(),
        "scenario": net[scenario].to_numpy(),
    }, index=net.index)
    lignes["variation_pct"] = 100.0 * (lignes["scenario"] / lignes["reference"] - 1.0)
    lignes["publie_pct"] = [PUBLIES.get(s, {}).get("resultat_net_pct") for s in net.index]
    lignes["ecart_points"] = lignes["variation_pct"] - lignes["publie_pct"]
    return lignes.sort_values("variation_pct")


def trajectoire(table: pd.DataFrame, secteur: str, geographie: str = "Canada") -> pd.DataFrame:
    """Le résultat net d'un secteur, année par année, un scénario par colonne."""
    bloc = table[table.CL_GEOGRAPHY.eq(geographie) & table.CL_SECTOR.eq(secteur)
                 & table.CL_VARIABLE.isin(POSTES)]
    large = bloc.pivot_table(index=["CL_YEAR", "CL_SCENARIO"], columns="CL_VARIABLE",
                             values="CL_VALUE").dropna(subset=list(POSTES))
    net = (large["Revenue"] - large["Direct emissions costs"] - large["Indirect costs"])
    return net.unstack("CL_SCENARIO")
