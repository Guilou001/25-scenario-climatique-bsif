"""Ce que la mécanique du BSIF fait au-delà de son exemple : qui la majoration climatique frappe.

L'exemple officiel porte sur une seule exposition, un seul secteur, un seul seau de qualité. La
question qu'il ne pose pas est celle qui décide de la lecture d'un résultat d'exercice : à majoration
identique, quelle exposition voit sa perte attendue monter le plus ?

La réponse tient à la forme de la formule et se démontre en deux lignes. La majoration s'ajoute au
logit, donc la cote de défaut est multipliée par l'exponentielle de la majoration. Quand la
probabilité est petite, la cote est presque la probabilité, si bien que la probabilité elle-même est
multipliée par ce facteur. Quand la probabilité est grande, la cote est bien plus grande que la
probabilité, et la même multiplication de la cote déplace beaucoup moins la probabilité.

Autrement dit, **une majoration constante sur l'échelle logit fait monter en proportion la
probabilité de défaut d'un bon emprunteur plus que celle d'un mauvais**. Ce module le mesure, sur la
seule colonne de majorations que le BSIF publie.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .exemple import majorations_de
from .scse import SEAUX, Exposition, ecl_climatique, ecl_de_reference, logit, sigmoide

LGD_TYPE = 0.45          # perte en cas de défaut d'un prêt d'entreprise sans sûreté, hypothèse déclarée
TAUX_TYPE = 0.05         # taux d'actualisation, hypothèse déclarée
ECHEANCES = (1, 3, 5, 7, 10, 15, 20)


def milieu_de_seau(numero: int) -> float:
    """Le milieu géométrique d'un seau de qualité, borne haute du dernier seau ramenée à 40 %.

    Le milieu géométrique et non arithmétique, parce que les bornes des seaux croissent en ordre de
    grandeur : entre 0,25 % et 1 %, le milieu qui a un sens est 0,5 % et non 0,625 %.
    """
    bas, haut = next((b, h) for n, b, h in SEAUX if n == numero)
    bas = max(bas, 1e-4)
    haut = min(haut, 0.40)
    return float(np.sqrt(bas * haut))


def hausse_de_probabilite(pd_initiale, majoration: float) -> np.ndarray:
    """La hausse relative d'une probabilité de défaut, en pourcentage, pour une majoration donnée.

    C'est la formule seule, sans actualisation ni perte en cas de défaut : le mécanisme nu.
    """
    p = np.asarray(pd_initiale, dtype=float)
    return 100.0 * (sigmoide(logit(p) + majoration) / p - 1.0)


def exposition_type(pd_conditionnelle: float, annees: int, lgd: float = LGD_TYPE,
                    taux: float = TAUX_TYPE) -> Exposition:
    """Un prêt d'entreprise stylisé : hasard de défaut constant, exposition constante, un scénario.

    Le hasard constant est l'hypothèse la plus neutre possible : elle ne met aucune structure par
    terme dans le résultat, si bien que ce que la carte montre vient de la formule du BSIF et de rien
    d'autre.
    """
    survie = np.concatenate([[1.0], np.cumprod([1.0 - pd_conditionnelle] * annees)[:-1]])
    inconditionnelles = survie * pd_conditionnelle
    return Exposition(pd_par_scenario={"unique": inconditionnelles},
                      lgd=np.full(annees, lgd), ead=np.ones(annees),
                      poids={"unique": 1.0}, taux_actualisation=taux)


def carte(horizon: int = 2045, echeances=ECHEANCES) -> pd.DataFrame:
    """La hausse de la perte attendue, en pourcentage, par seau de qualité et par échéance.

    Une ligne par seau, une colonne par échéance en années. Les majorations sont celles du charbon
    canadien au seau 4, seule colonne publiée : elles sont appliquées à tous les seaux, ce qui est
    une hypothèse et non une lecture du BSIF, et qui est exactement ce qu'il faut pour isoler l'effet
    de la formule.
    """
    lignes = []
    for numero, _, _ in SEAUX:
        h = milieu_de_seau(numero)
        ligne = {"seau": numero, "pd_conditionnelle": h}
        for annees in echeances:
            exposition = exposition_type(h, annees)
            reference = ecl_de_reference(exposition)["ponderee"]
            climatique = ecl_climatique(exposition, majorations_de(horizon, annees))["ponderee"]
            ligne[f"{annees} ans"] = 100.0 * (climatique / reference - 1.0)
        lignes.append(ligne)
    return pd.DataFrame(lignes).set_index("seau")


def rapport_extremes(table: pd.DataFrame, colonne: str) -> float:
    """Combien de fois la hausse du meilleur seau dépasse celle du pire, à échéance donnée."""
    return float(table[colonne].iloc[0] / table[colonne].iloc[-1])


def par_horizon(seau: int = 4, annees: int = 6) -> pd.DataFrame:
    """La hausse de la perte attendue aux quatre horizons de l'exercice, pour un seau donné."""
    from .exemple import HORIZONS

    exposition = exposition_type(milieu_de_seau(seau), annees)
    reference = ecl_de_reference(exposition)["ponderee"]
    lignes = [{"horizon": h,
               "hausse_pct": 100.0 * (ecl_climatique(
                   exposition, majorations_de(h, annees))["ponderee"] / reference - 1.0)}
              for h in HORIZONS]
    return pd.DataFrame(lignes).set_index("horizon")
