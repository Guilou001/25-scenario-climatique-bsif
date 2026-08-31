"""L'exemple travaillé du BSIF, recopié chiffre par chiffre : c'est la vérité connue du dépôt.

Le classeur d'instructions de l'exercice normalisé porte un onglet « Credit Risk Example » qui déroule
un cas complet, tous les intermédiaires imprimés en double précision. C'est ce qui fait de ce module
de calcul un objet vérifiable plutôt qu'une interprétation : il ne s'agit pas de coder une méthode
plausible, il s'agit de retrouver des nombres déjà publiés.

Les constantes ci-dessous sont ces nombres. Elles ne sont pas retapées de mémoire : `lire_exemple()`
les ré-extrait du classeur téléchargé et `scc verifier` compare les deux, si bien qu'une faute de
frappe se voit.

L'exposition du cas : trois millions de dollars sur le secteur du charbon au Canada, prêt d'entreprise
soumis à la norme IFRS 9, six ans de vie restante, taux d'actualisation de 10 %, trois scénarios
macroéconomiques pondérés 60, 30 et 10 %.
"""

from __future__ import annotations

import numpy as np

SCENARIOS = ("pessimiste", "base", "optimiste")
POIDS = {"pessimiste": 0.6, "base": 0.3, "optimiste": 0.1}
TAUX_ACTUALISATION = 0.10

# Probabilités de défaut inconditionnelles, années 2024 à 2029, telles que l'institution les estime
# pour sa perte attendue comptable, avant tout climat.
PD_INCONDITIONNELLES = {
    "pessimiste": np.array([0.04, 0.035, 0.03, 0.025, 0.02, 0.015]),
    "base": np.array([0.03, 0.025, 0.02, 0.015, 0.01, 0.005]),
    "optimiste": np.array([0.025, 0.02, 0.025, 0.01, 0.005, 0.0025]),
}
LGD = np.array([0.8, 0.7, 0.6, 0.5, 0.5, 0.5])
EAD = np.array([3_000_000.0, 2_500_000.0, 2_000_000.0, 1_500_000.0, 1_000_000.0, 500_000.0])

# Perte de crédit attendue de référence, publiée par le BSIF.
ECL_REFERENCE = {"pessimiste": 186_072.38757231616, "base": 131_137.2258702918,
                 "optimiste": 113_038.21883638216}
ECL_REFERENCE_PONDEREE = 162_288.42218811542
PD_PONDEREE_PREMIERE_ANNEE = 0.035500000000000004
SEAU_ATTENDU = 4

# Majorations climatiques prescrites, secteur du charbon, Canada, seau de qualité 4, scénario
# « sous 2 °C immédiat ». Une par année civile, de 2030 à 2050.
MAJORATIONS = {
    2030: 0.045,
    2031: 0.0465,
    2032: 0.04805,
    2033: 0.04965166666666667,
    2034: 0.051306722222222226,
    2035: 0.0530169462962963,
    2036: 0.054784177839506176,
    2037: 0.05661031710082305,
    2038: 0.05849732767085049,
    2039: 0.060447238593212174,
    2040: 0.06246214654631925,
    2041: 0.06454421809786323,
    2042: 0.06669569203445867,
    2043: 0.06891888176894063,
    2044: 0.07121617782790532,
    2045: 0.07359005042216883,
    2046: 0.0760430521029078,
    2047: 0.07857782050633805,
    2048: 0.08119708118988266,
    2049: 0.08390365056287874,
    2050: 0.0867004389149747,
}

# L'horizon 2045 déroulé en entier dans le classeur, années 2046 à 2051, scénario pessimiste.
PD_CLIMATIQUES_2045_PESSIMISTE = np.array([
    0.04302438846819852, 0.03762973483900741, 0.032250179517259135,
    0.026882265617533107, 0.0215212352223683, 0.01611516965341332])
LGD_CLIMATIQUES_2045_PESSIMISTE = np.array([
    0.8024154660853956, 0.7031874582378387, 0.6036898568939904,
    0.5039294814172207, 0.5037302458109812, 0.5033852415597501])
ECL_CLIMATIQUE_2045 = {"pessimiste": 200_980.4890340063, "base": 141_800.15051198396,
                       "optimiste": 122_290.10021179203}

# La ligne que l'institution reporterait dans le classeur, un horizon par colonne.
ECL_PAR_HORIZON = {2030: 170_170.0115186833, 2035: 171_611.30691219494,
                   2040: 173_324.04683538934, 2045: 175_357.3485951782}

HORIZONS = (2030, 2035, 2040, 2045)


def majorations_de(horizon: int, annees: int) -> np.ndarray:
    """Les majorations d'un horizon, une par année de vie restante.

    L'horizon T ouvre sur l'année T plus un. Quand la vie de l'exposition dépasse 2050, dernière
    année publiée, le BSIF prescrit de prolonger la dernière majoration : c'est la règle du
    paragraphe qui suit le tableau, et elle est appliquée telle quelle.
    """
    derniere = max(MAJORATIONS)
    return np.array([MAJORATIONS[min(horizon + i, derniere)] for i in range(1, annees + 1)])


def exposition():
    """L'exposition du cas, prête à passer dans `scse`."""
    from .scse import Exposition

    return Exposition(pd_par_scenario={k: v.copy() for k, v in PD_INCONDITIONNELLES.items()},
                      lgd=LGD.copy(), ead=EAD.copy(), poids=dict(POIDS),
                      taux_actualisation=TAUX_ACTUALISATION)


class ClasseurInattendu(LookupError):
    """Le classeur ne porte pas un libellé attendu. Mieux vaut s'arrêter que lire à côté."""


def _ligne_du_libelle(lignes, libelle: str, colonne: int = 0) -> int:
    """Le rang de la première ligne dont la colonne donnée porte exactement ce libellé.

    Compter les lignes en dur casserait en silence : le BSIF publie déjà ce classeur sous le suffixe
    `_2`, donc il le révise, et deux lignes insérées feraient lire les cellules voisines sans lever
    d'erreur. Le libellé, lui, se déplace avec son bloc.
    """
    for i, ligne in enumerate(lignes):
        valeur = ligne[colonne] if colonne < len(ligne) else None
        if isinstance(valeur, str) and valeur.strip() == libelle:
            return i
    raise ClasseurInattendu(f"libellé « {libelle} » introuvable en colonne {colonne + 1}")


def _premiere_annee(lignes, depart: int) -> int:
    """Le rang de la première ligne, à partir de `depart`, dont la colonne A porte une année."""
    for i in range(depart, len(lignes)):
        valeur = lignes[i][0]
        if isinstance(valeur, int) and not isinstance(valeur, bool) and 1900 < valeur < 2200:
            return i
    raise ClasseurInattendu(f"aucune année en colonne A après la ligne {depart + 1}")


def lire_exemple(classeur) -> dict:
    """Les mêmes nombres, ré-extraits du classeur d'instructions téléchargé.

    Sert à prouver que les constantes de ce fichier sont bien celles du BSIF et non une transcription
    approximative. Exige le fichier, donc le réseau au moins une fois : les tests, eux, tournent sur
    les constantes.

    Chaque bloc est ancré sur un libellé du classeur, jamais sur un numéro de ligne.
    """
    import openpyxl

    feuille = openpyxl.load_workbook(classeur, read_only=True, data_only=True)["Credit Risk Example"]
    lignes = [list(r) for r in feuille.iter_rows(values_only=True)]

    def bloc(depart: int, colonnes: range, hauteur: int = 6):
        return np.array([[lignes[depart + i][c] for c in colonnes] for i in range(hauteur)],
                        dtype=float)

    # le bloc de référence suit le libellé « Years in the Lifetime of the exposure », qui apparaît
    # deux fois dans l'onglet : la première occurrence est bien celle d'avant climat
    reference = _premiere_annee(
        lignes, _ligne_du_libelle(lignes, "Years in the Lifetime of the exposure"))
    # la probabilité INCONDITIONNELLE est en colonne B et la perte en cas de défaut en colonne E. Le
    # bloc des probabilités conditionnelles porte, lui, la CONDITIONNELLE en colonne E, et les
    # confondre décale les six valeurs de trois millièmes.
    climatique = _premiere_annee(
        lignes, _ligne_du_libelle(lignes, "Years in the Lifetime for the snapshot"))
    total_reference = _ligne_du_libelle(lignes, "Total ECL", colonne=6)
    total_climatique = _ligne_du_libelle(lignes, "Total ECL", colonne=3)
    majorations_debut = _premiere_annee(lignes, _ligne_du_libelle(lignes, "year"))
    # la ligne que l'institution reporterait : elle suit l'en-tête du bloc « SCSE Workbook », et
    # c'est la seule dont la colonne A nomme un secteur
    entete_releve = _ligne_du_libelle(lignes, "industry_sector")
    releve = _ligne_du_libelle(lignes[entete_releve:], "COAL") + entete_releve

    pd_ref = bloc(reference, range(1, 4))
    majorations = {int(lignes[majorations_debut + i][0]): float(lignes[majorations_debut + i][4])
                   for i in range(21)}
    return {
        "pd_inconditionnelles": {nom: pd_ref[:, j] for j, nom in enumerate(SCENARIOS)},
        "lgd": bloc(reference, range(4, 5)).ravel(),
        "ead": bloc(reference, range(5, 6)).ravel(),
        "ecl_reference": {nom: float(lignes[total_reference][11 + j])
                          for j, nom in enumerate(SCENARIOS)},
        "ecl_reference_ponderee": float(lignes[total_reference][14]),
        "pd_climatiques_2045_pessimiste": bloc(climatique, range(1, 2)).ravel(),
        "lgd_climatiques_2045_pessimiste": bloc(climatique, range(4, 5)).ravel(),
        "ecl_climatique_2045": {nom: float(lignes[total_climatique][8 + j])
                                for j, nom in enumerate(SCENARIOS)},
        "ecl_par_horizon": {h: float(lignes[releve][6 + j]) for j, h in enumerate(HORIZONS)},
        "majorations": majorations,
    }
