"""Le module de crédit de l'exercice normalisé, écrit depuis les formules publiées par le BSIF.

L'**exercice normalisé de scénarios climatiques** est le calcul que le Bureau du surintendant des
institutions financières impose depuis 2024 à toutes les institutions financières fédérales. Chacune
doit dire de combien sa perte de crédit attendue se déplacerait sous trois trajectoires de transition
climatique, à quatre horizons. Le BSIF publie la méthode, le classeur à remplir et un exemple
travaillé complet. Ce module est cet exemple, réécrit en Python.

Quatre formules suffisent, et elles s'enchaînent dans cet ordre.

1. **Passer à la probabilité conditionnelle.** La probabilité inconditionnelle de faire défaut à
   l'année i est celle de défaillir cette année-là vu d'aujourd'hui. La conditionnelle est celle de
   défaillir sachant qu'on a survécu jusque-là. La seconde se déduit de la première en divisant par
   la probabilité de survie accumulée.
2. **Ajouter la majoration climatique sur l'échelle logit.** Le logit d'une probabilité est le
   logarithme de sa cote, `ln(p / (1 - p))`. Le BSIF prescrit une majoration par secteur, région et
   seau de qualité, et elle s'ajoute au logit, jamais à la probabilité elle-même. C'est ce choix qui
   garantit que le résultat reste entre zéro et un, et c'est aussi lui qui fait monter en proportion
   la probabilité de défaut d'un bon emprunteur plus que celle d'un mauvais.
3. **Revenir à l'inconditionnel** en remultipliant par les survies climatiques.
4. **Ajuster la perte en cas de défaut par la relation de Frye-Jacobs**, qui lie perte et probabilité
   de défaut par un seul paramètre. Quand la probabilité de défaut monte, la perte en cas de défaut
   monte aussi, parce que les défaillances se concentrent dans les mauvaises années où les garanties
   valent moins.

La perte de crédit attendue est enfin la somme actualisée, année par année, du produit de la
probabilité inconditionnelle, de la perte en cas de défaut et de l'exposition.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

# Les seaux de qualité de crédit du BSIF, bornes inférieures incluses et supérieures exclues, lues
# dans l'onglet « Credit Quality Buckets » du classeur d'instructions.
SEAUX = [(1, 0.0, 0.0007), (2, 0.0007, 0.0025), (3, 0.0025, 0.01),
         (4, 0.01, 0.07), (5, 0.07, 0.2), (6, 0.2, 1.0)]

# Les facteurs simplifiés du chapitre 3.4 : ce que le BSIF autorise à déclarer sans modèle.
SCENARIOS = ("Sous 2 °C immédiat", "Sous 2 °C retardé", "Carboneutre 2050")


def logit(p):
    """Le logarithme de la cote. C'est l'échelle sur laquelle la majoration climatique s'ajoute."""
    p = np.asarray(p, dtype=float)
    return np.log(p / (1.0 - p))


def sigmoide(x):
    """L'inverse du logit, qui ramène n'importe quel réel dans l'intervalle des probabilités."""
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))


def conditionnelles(inconditionnelles) -> tuple[np.ndarray, np.ndarray]:
    """Les probabilités de défaut conditionnelles, et les facteurs de survie qui les produisent.

    La probabilité conditionnelle de l'année i vaut l'inconditionnelle divisée par la survie
    accumulée jusqu'à l'année i moins un. Sur l'exemple du BSIF, 3,5 % d'inconditionnelle en
    deuxième année sur une survie de 96 % donne 3,6458 % de conditionnelle.
    """
    inconditionnelles = np.asarray(inconditionnelles, dtype=float)
    cpd, survies, accumulee = [], [], 1.0
    for p in inconditionnelles:
        c = p / accumulee
        cpd.append(c)
        accumulee *= 1.0 - c
        survies.append(1.0 - c)
    return np.array(cpd), np.array(survies)


def inconditionnelles(conditionnelles_annuelles) -> np.ndarray:
    """Le chemin inverse : de la conditionnelle à l'inconditionnelle, par le produit des survies."""
    c = np.asarray(conditionnelles_annuelles, dtype=float)
    survie = np.concatenate([[1.0], np.cumprod(1.0 - c)[:-1]])
    return survie * c


def pd_climatiques(pd_inconditionnelles, majorations) -> np.ndarray:
    """Les probabilités de défaut inconditionnelles après la majoration climatique du BSIF.

    Le passage par le conditionnel n'est pas une élégance : ajouter la majoration directement à
    l'inconditionnelle donnerait un résultat qui dépend de l'ordre des années, ce qu'une probabilité
    de survie ne peut pas faire.
    """
    cpd, _ = conditionnelles(pd_inconditionnelles)
    return inconditionnelles(sigmoide(logit(cpd) + np.asarray(majorations, dtype=float)))


def lgd_frye_jacobs(pd_climatique, pd_initiale, lgd_initiale) -> np.ndarray:
    """La perte en cas de défaut ajustée, par la relation à un paramètre de Frye et Jacobs.

    Elle dit une chose simple : la perte attendue, produit de la probabilité de défaut et de la
    perte en cas de défaut, se déplace le long d'une même courbe quand le risque monte. Comme la
    probabilité de défaut monte plus vite que la perte attendue, la perte en cas de défaut monte
    aussi, mais peu. Sur l'exemple du BSIF, 80,00 % devient 80,24 % pour une probabilité de défaut
    qui passe de 4,00 % à 4,30 %.
    """
    pd_climatique = np.asarray(pd_climatique, dtype=float)
    pd_initiale = np.asarray(pd_initiale, dtype=float)
    lgd_initiale = np.asarray(lgd_initiale, dtype=float)
    perte_attendue = norm.cdf(norm.ppf(pd_climatique) - norm.ppf(pd_initiale)
                              + norm.ppf(pd_initiale * lgd_initiale))
    return perte_attendue / pd_climatique


def perte_attendue(pd_annuelles, lgd_annuelles, ead_annuelles, taux: float = 0.10) -> dict:
    """La perte de crédit attendue sur la durée de vie, actualisée au taux donné.

    L'actualisation commence à la fin de la première année, comme dans le classeur du BSIF : le
    facteur de la première année vaut un sur un plus le taux, et non un.
    """
    pd_annuelles = np.asarray(pd_annuelles, dtype=float)
    annuelle = pd_annuelles * np.asarray(lgd_annuelles, dtype=float) * np.asarray(ead_annuelles,
                                                                                 dtype=float)
    escompte = np.array([1.0 / (1.0 + taux) ** (i + 1) for i in range(len(annuelle))])
    return {"annuelle": annuelle, "escompte": escompte, "totale": float((annuelle * escompte).sum())}


def seau_qualite(pd_ponderee: float) -> int:
    """Le seau de qualité de crédit du BSIF, déterminé sur la probabilité de la première année.

    Les bornes sont inférieures incluses et supérieures exclues, ce qui compte : une probabilité de
    0,0025 tombe dans le seau 3 et non dans le seau 2.
    """
    for numero, bas, haut in SEAUX:
        if bas <= pd_ponderee < haut:
            return numero
    return SEAUX[-1][0]


@dataclass(frozen=True)
class Exposition:
    """Une exposition telle que le classeur du BSIF la décrit, scénario macroéconomique par scénario.

    Les probabilités de défaut, les pertes en cas de défaut et les expositions sont annuelles, sur la
    durée de vie restante. Les poids sont ceux que l'institution emploie déjà pour sa perte attendue
    comptable, et le BSIF impose de reprendre les mêmes.
    """

    pd_par_scenario: dict[str, np.ndarray]
    lgd: np.ndarray
    ead: np.ndarray
    poids: dict[str, float]
    taux_actualisation: float = 0.10

    def __post_init__(self):
        somme = sum(self.poids.values())
        if abs(somme - 1.0) > 1e-9:
            raise ValueError(f"les poids des scénarios doivent sommer à un, ils somment à {somme}")
        if set(self.poids) != set(self.pd_par_scenario):
            raise ValueError("chaque scénario pondéré doit avoir sa trajectoire de probabilités")


def ecl_de_reference(exposition: Exposition) -> dict:
    """La perte de crédit attendue avant tout climat : celle de la comptabilité, pondérée.

    C'est le point de comparaison de tout l'exercice. Le seau de qualité s'en déduit, sur la
    probabilité pondérée de la première année.
    """
    par_scenario = {nom: perte_attendue(pd, exposition.lgd, exposition.ead,
                                        exposition.taux_actualisation)["totale"]
                    for nom, pd in exposition.pd_par_scenario.items()}
    ponderee = sum(exposition.poids[nom] * v for nom, v in par_scenario.items())
    pd_premiere = sum(exposition.poids[nom] * pd[0] for nom, pd in exposition.pd_par_scenario.items())
    return {"par_scenario": par_scenario, "ponderee": ponderee,
            "pd_ponderee": pd_premiere, "seau": seau_qualite(pd_premiere)}


def ecl_climatique(exposition: Exposition, majorations) -> dict:
    """La perte attendue après la majoration climatique, par scénario puis pondérée.

    Les majorations sont celles de l'horizon retenu, une par année de vie restante.
    """
    majorations = np.asarray(majorations, dtype=float)
    if len(majorations) != len(exposition.lgd):
        raise ValueError("il faut une majoration par année de vie restante")

    detail, par_scenario = {}, {}
    for nom, pd in exposition.pd_par_scenario.items():
        pd_clim = pd_climatiques(pd, majorations)
        lgd_clim = lgd_frye_jacobs(pd_clim, pd, exposition.lgd)
        perte = perte_attendue(pd_clim, lgd_clim, exposition.ead, exposition.taux_actualisation)
        detail[nom] = {"pd": pd_clim, "lgd": lgd_clim, "annuelle": perte["annuelle"]}
        par_scenario[nom] = perte["totale"]
    ponderee = sum(exposition.poids[nom] * v for nom, v in par_scenario.items())
    return {"detail": detail, "par_scenario": par_scenario, "ponderee": ponderee}


def hausse_relative(exposition: Exposition, majorations) -> float:
    """De combien, en pourcentage, la majoration climatique déplace la perte attendue pondérée."""
    reference = ecl_de_reference(exposition)["ponderee"]
    return 100.0 * (ecl_climatique(exposition, majorations)["ponderee"] / reference - 1.0)
