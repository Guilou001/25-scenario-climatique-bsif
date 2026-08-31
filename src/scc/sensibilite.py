"""Ce que la mécanique du BSIF fait au-delà de son exemple : qui la majoration climatique frappe.

L'exemple officiel porte sur une seule exposition, un seul secteur, un seul seau de qualité. La
question qu'il ne pose pas est celle qui décide de la lecture d'un résultat d'exercice : à majoration
identique, quelle exposition voit sa perte attendue monter le plus ?

La réponse tient à la forme de la formule et se démontre en deux lignes. La majoration s'ajoute au
logit, donc la cote de défaut est multipliée par l'exponentielle de la majoration. Quand la
probabilité est petite, la cote est presque la probabilité, si bien que la probabilité elle-même est
multipliée par ce facteur. Quand la probabilité est grande, la cote est bien plus grande que la
probabilité, et la même multiplication de la cote déplace beaucoup moins la probabilité.

Autrement dit, une majoration constante sur l'échelle logit fait monter en proportion la probabilité
de défaut d'un bon emprunteur plus que celle d'un mauvais. Ce module le mesure, sur la seule colonne
de majorations que le BSIF publie.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .exemple import majorations_de
from .scse import (
    SEAUX,
    Exposition,
    ecl_climatique,
    ecl_de_reference,
    logit,
    pd_climatiques,
    perte_attendue,
    sigmoide,
)

LGD_TYPE = 0.45          # perte en cas de défaut d'un prêt d'entreprise sans sûreté, hypothèse déclarée
TAUX_TYPE = 0.05         # taux d'actualisation, hypothèse déclarée
ECHEANCES = (1, 3, 5, 7, 10, 15, 20)


PLANCHER = 1e-4          # la borne basse du premier seau, voir `milieu_de_seau`
PLAFOND = 0.40           # la borne haute du dernier seau, voir `milieu_de_seau`


def milieu_de_seau(numero: int) -> float:
    """Le milieu géométrique d'un seau de qualité, ses deux bornes extrêmes ramenées à des valeurs finies.

    Le milieu géométrique et non arithmétique, parce que les bornes des seaux croissent en ordre de
    grandeur : entre 0,25 % et 1 %, le milieu qui a un sens est 0,5 % et non 0,625 %.

    Deux bornes du BSIF ne se prêtent pas à cette moyenne, et les deux sont remplacées ici. Le
    premier seau part de zéro, dont le milieu géométrique n'existe pas : il est relevé à 1 point de
    base, ce qui donne la probabilité de 0,03 % du premier seau. Le dernier seau monte à 100 %, ce
    qui décrirait un emprunteur déjà en défaut : il est ramené à 40 %. Les deux sont des hypothèses,
    et le premier n'est pas neutre. Mesuré en faisant varier le plancher de 1e-3 à 1e-6, la hausse
    du seau 1 à vingt ans va de 9,342 % à 9,221 % et le rapport entre extrêmes de 5,902 à 5,825.
    """
    bas, haut = next((b, h) for n, b, h in SEAUX if n == numero)
    bas = max(bas, PLANCHER)
    haut = min(haut, PLAFOND)
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

    Le hasard constant est l'hypothèse la plus neutre possible. Elle ne met aucune structure par
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
    canadien au seau 4, seule colonne publiée, et elles sont appliquées à tous les seaux. C'est une
    hypothèse et non une lecture du BSIF, et c'est exactement ce qu'il faut pour isoler l'effet de la
    formule.
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


def reconciliation(horizon: int = 2045, annees: int = 20) -> pd.DataFrame:
    """Ce qui sépare le plafond de la figure de la mécanique des hausses de la carte.

    Deux différences, et un seul tableau pour les deux. La figure ne porte qu'une majoration, celle
    de 2046, et ne fait monter que la probabilité de défaut. La carte emploie tout le chemin de
    majorations, de 2046 à 2050 puis prolongé, et porte la perte attendue, perte en cas de défaut
    comprise. D'où deux plafonds, `exp(0,076 043) - 1` pour la figure et `exp(0,086 700) - 1` pour le
    chemin, et une colonne de plus entre la hausse de la seule probabilité et celle de la perte
    attendue.
    """
    majorations = majorations_de(horizon, annees)
    lignes = []
    for numero, _, _ in SEAUX:
        p = milieu_de_seau(numero)
        exposition = exposition_type(p, annees)
        pd_clim = pd_climatiques(exposition.pd_par_scenario["unique"], majorations)
        reference = ecl_de_reference(exposition)["ponderee"]
        sans_lgd = perte_attendue(pd_clim, exposition.lgd, exposition.ead,
                                  exposition.taux_actualisation)["totale"]
        avec_lgd = ecl_climatique(exposition, majorations)["ponderee"]
        lignes.append({
            "seau": numero,
            "hausse_pd_majoration_2046_pct": float(hausse_de_probabilite(p, majorations[0])),
            "hausse_ecl_sans_ajustement_lgd_pct": 100.0 * (sans_lgd / reference - 1.0),
            "hausse_ecl_pct": 100.0 * (avec_lgd / reference - 1.0),
        })
    table = pd.DataFrame(lignes).set_index("seau")
    table["plafond_majoration_2046_pct"] = 100.0 * (np.exp(majorations[0]) - 1.0)
    table["plafond_chemin_complet_pct"] = 100.0 * (np.exp(majorations.max()) - 1.0)
    return table
