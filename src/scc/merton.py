"""Le maillon manquant, retourné : quel emprunteur faudrait-il pour que +450 % de PD en découle ?

Le rapport de 2022 ne permet pas de reconstruire sa hausse de probabilité de défaut, faute des
évaluations d'emprunteurs qui la calibrent. Il reste une question qui, elle, se répond : dans le
modèle de structure le plus simple, celui de Merton, quel niveau d'endettement un emprunteur devrait
avoir pour qu'une baisse de valeur de 71 % multiplie sa probabilité de défaut par 5,5 ?

Le **modèle de Merton** traite les capitaux propres d'une entreprise comme une option d'achat sur ses
actifs : l'actionnaire ne rembourse la dette que si les actifs valent plus qu'elle, et fait défaut
sinon. La probabilité de défaut est donc celle que la valeur des actifs tombe sous la dette à
l'échéance, et elle ne dépend que de trois choses, le rapport de la dette à l'actif, la volatilité de
l'actif et l'horizon.

Ce que ce module calcule N'EST PAS ce que la Banque du Canada a fait, et le README le dit. C'est une
question différente, posée au même chiffre : ce chiffre est-il celui d'un emprunteur ordinaire ou
d'un emprunteur déjà fragile ?
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

# La baisse de valeur retenue par défaut est celle que le fichier public donne pour les produits
# pétroliers raffinés en 2050, sous « sous 2 °C immédiat », mesurée par le module `scenarios`.
CHOC_RAFFINAGE = 0.711
RATIO_PUBLIE = 5.5          # +450 % de probabilité de défaut, donc 5,5 fois


def probabilite_de_defaut(levier: float, volatilite: float, horizon: float = 5.0,
                          derive: float = 0.0) -> float:
    """La probabilité que l'actif tombe sous la dette à l'horizon, sous le modèle de Merton.

    Le levier est le rapport de la dette à la valeur d'actif d'aujourd'hui : 0,4 veut dire que la
    dette vaut 40 % de l'actif. La dérive est le rendement attendu de l'actif, prise nulle par défaut
    pour n'introduire aucune vue de marché dans le résultat.
    """
    if not 0.0 < levier < 1.0 or volatilite <= 0.0 or horizon <= 0.0:
        raise ValueError("levier dans (0, 1), volatilité et horizon strictement positifs")
    return float(np.exp(_log_probabilite(levier, volatilite, horizon, derive)))


def _log_probabilite(levier: float, volatilite: float, horizon: float, derive: float) -> float:
    """Le logarithme de la probabilité de défaut.

    Un emprunteur peu endetté a une probabilité si petite qu'elle s'annule en flottant, ce qui ferait
    échouer le rapport de deux probabilités. Le logarithme, lui, reste représentable, et le rapport
    se calcule par une différence.
    """
    distance = (-np.log(levier) + (derive - 0.5 * volatilite ** 2) * horizon) / (
        volatilite * np.sqrt(horizon))
    return float(norm.logcdf(-distance))


def ratio_apres_choc(levier: float, choc: float, volatilite: float, horizon: float = 5.0,
                     derive: float = 0.0) -> float:
    """Par combien la probabilité de défaut est multipliée quand l'actif perd la fraction `choc`.

    Un choc de 0,711 signifie que l'actif ne vaut plus que 28,9 % de sa valeur : le levier est donc
    divisé par 0,289. C'est l'hypothèse de passage du résultat net à la valeur d'actif, et c'est une
    hypothèse déclarée, pas une lecture du rapport.
    """
    if not 0.0 < levier < 1.0 or not 0.0 <= choc < 1.0:
        raise ValueError("levier dans (0, 1) et choc dans [0, 1)")
    avant = _log_probabilite(levier, volatilite, horizon, derive)
    apres = _log_probabilite(min(levier / (1.0 - choc), 1.0 - 1e-12), volatilite, horizon, derive)
    # un emprunteur sans dette a une probabilité si petite que le rapport déborde le flottant : le
    # dire plutôt que de laisser numpy prévenir et rendre l'infini
    return float("inf") if apres - avant > 700.0 else float(np.exp(apres - avant))


def levier_requis(ratio_cible: float = RATIO_PUBLIE, choc: float = CHOC_RAFFINAGE,
                  volatilite: float = 0.25, horizon: float = 5.0, derive: float = 0.0) -> float:
    """Le levier qui produit exactement le rapport de probabilités visé.

    Le rapport décroît quand le levier monte : un emprunteur déjà proche du défaut ne peut pas voir
    sa probabilité quintupler, elle est déjà trop haute. La solution est donc unique et se trouve par
    dichotomie.
    """
    def ecart(levier):
        return ratio_apres_choc(levier, choc, volatilite, horizon, derive) - ratio_cible

    bas, haut = 1e-12, 1.0 - 1e-9
    if ecart(haut) > 0.0:
        return float("nan")     # même un emprunteur au bord du défaut dépasse la cible
    if ecart(bas) < 0.0:
        return float("nan")     # même un emprunteur sans dette ne l'atteint pas
    return float(brentq(ecart, bas, haut, xtol=1e-14, rtol=1e-13))


def courbe_levier(volatilites=None, ratio_cible: float = RATIO_PUBLIE,
                  choc: float = CHOC_RAFFINAGE, horizon: float = 5.0):
    """Le levier requis en fonction de la volatilité d'actif, et la probabilité de défaut de départ.

    Renvoie trois tableaux de même longueur : volatilités, leviers requis, probabilités de défaut
    initiales correspondantes. La troisième est celle qui répond à la question posée, parce qu'une
    probabilité de départ se compare à une notation.
    """
    volatilites = np.asarray(volatilites if volatilites is not None
                             else np.linspace(0.10, 0.60, 51), dtype=float)
    leviers = np.array([levier_requis(ratio_cible, choc, float(v), horizon) for v in volatilites])
    depart = np.array([probabilite_de_defaut(float(lev), float(v), horizon)
                       if np.isfinite(lev) else np.nan
                       for lev, v in zip(leviers, volatilites, strict=True)])
    return volatilites, leviers, depart
