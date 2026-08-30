"""Les trois analyses qui vont au-delà de l'exemple : la mécanique, la carte, l'inversion."""

import numpy as np
import pytest

from scc.exemple import MAJORATIONS
from scc.merton import (
    courbe_levier,
    levier_requis,
    probabilite_de_defaut,
    ratio_apres_choc,
)
from scc.scenarios import PUBLIES, charger, variation
from scc.sensibilite import carte, hausse_de_probabilite, milieu_de_seau, rapport_extremes

MAJORATION = MAJORATIONS[2046]


def test_la_hausse_relative_plafonne_a_l_exponentielle_de_la_majoration():
    """Quand la probabilité tend vers zéro, la cote tend vers elle, donc la hausse tend vers e^a - 1.
    C'est le mécanisme entier, en une limite."""
    plafond = 100.0 * (np.exp(MAJORATION) - 1.0)
    assert hausse_de_probabilite(1e-9, MAJORATION) == pytest.approx(plafond, abs=1e-5)
    assert hausse_de_probabilite(0.001, MAJORATION) < plafond


def test_la_hausse_relative_decroit_avec_la_probabilite_de_depart():
    grille = np.array([1e-4, 1e-3, 1e-2, 0.05, 0.1, 0.3, 0.5])
    hausses = hausse_de_probabilite(grille, MAJORATION)
    assert np.all(np.diff(hausses) < 0.0)


def test_le_meilleur_seau_souffre_plus_que_le_pire_a_longue_echeance():
    """Le résultat du dépôt : la formule concentre la hausse sur les bons emprunteurs longs."""
    table = carte()
    assert table["20 ans"].iloc[0] > table["20 ans"].iloc[-1]
    assert rapport_extremes(table, "20 ans") > rapport_extremes(table, "1 ans")


def test_les_milieux_de_seaux_sont_croissants_et_dans_leurs_bornes():
    milieux = [milieu_de_seau(n) for n in range(1, 7)]
    assert np.all(np.diff(milieux) > 0.0)
    assert 0.0 < milieux[0] < 0.0007
    assert 0.2 < milieux[-1] < 0.4


def test_la_probabilite_de_merton_croit_avec_le_levier():
    assert probabilite_de_defaut(0.2, 0.25) < probabilite_de_defaut(0.6, 0.25)
    assert 0.0 < probabilite_de_defaut(0.6, 0.25) < 1.0


def test_un_choc_nul_laisse_la_probabilite_inchangee():
    assert ratio_apres_choc(0.4, 0.0, 0.25) == pytest.approx(1.0, abs=1e-12)


def test_l_inversion_retrouve_exactement_sa_cible():
    """Le test qui vérifie la dichotomie : réinjecter la solution doit redonner la cible."""
    for volatilite in (0.15, 0.25, 0.35):
        levier = levier_requis(volatilite=volatilite)
        assert ratio_apres_choc(levier, 0.711, volatilite) == pytest.approx(5.5, rel=1e-9)


def test_l_emprunteur_requis_est_deja_fragile():
    """Le verdict : pour que la probabilité quintuple, elle doit partir de plusieurs pour cent."""
    for volatilite in (0.15, 0.20, 0.25, 0.30):
        levier = levier_requis(volatilite=volatilite)
        depart = probabilite_de_defaut(levier, volatilite)
        assert 0.09 < depart < 0.12


def test_un_emprunteur_sans_dette_ne_deborde_pas_le_flottant():
    """Le piège numérique : sa probabilité de défaut s'annule en flottant, et la première version
    la mettait au dénominateur. Le calcul passe donc par les logarithmes, ce qui repousse la limite
    de 1e-12 à 1e-300, et au-delà l'infini est rendu au lieu d'un avertissement de numpy."""
    enorme = ratio_apres_choc(1e-12, 0.711, 0.25)
    assert np.isfinite(enorme) and enorme > 1e40
    assert ratio_apres_choc(1e-300, 0.711, 0.25) == float("inf")


def test_la_courbe_rend_trois_tableaux_de_meme_longueur():
    volatilites, leviers, depart = courbe_levier(np.linspace(0.15, 0.35, 5))
    assert len(volatilites) == len(leviers) == len(depart) == 5
    assert np.all(np.diff(leviers) < 0.0)      # plus l'actif est volatil, moins il faut de dette


def _fichier_bdc(chemin):
    """Un fichier au format de la Banque du Canada : bloc d'en-tête, puis les observations."""
    lignes = ['"TERMS AND CONDITIONS"', '"https://www.bankofcanada.ca/terms/"', "",
              '"OBSERVATIONS"',
              '"k","CL_GEOGRAPHY","CL_SECTOR","CL_VARIABLE","CL_UNIT","CL_SCENARIO","CL_YEAR",'
              '"CL_VALUE"']
    k = 0
    for scenario, (revenu, direct, indirect) in {
            "Baseline (2019 policies)": (100.0, 10.0, 20.0),
            "Below 2°C immediate": (80.0, 25.0, 25.0)}.items():
        for variable, valeur in [("Revenue", revenu), ("Direct emissions costs", direct),
                                 ("Indirect costs", indirect)]:
            k += 1
            lignes.append(f'"{k}","Canada","Refined oil products","{variable}","10 BN US$2014",'
                          f'"{scenario}","2050","{valeur}"')
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return chemin


def test_le_fichier_se_lit_apres_son_bloc_d_en_tete(tmp_path):
    """Compter les lignes d'en-tête casserait au premier changement : la ligne se cherche."""
    table = charger(_fichier_bdc(tmp_path / "mini.csv"))
    assert list(table.columns) == ["k", "CL_GEOGRAPHY", "CL_SECTOR", "CL_VARIABLE", "CL_UNIT",
                                   "CL_SCENARIO", "CL_YEAR", "CL_VALUE"]
    assert len(table) == 6 and table.CL_YEAR.dtype.kind == "i"


def test_le_resultat_net_est_les_produits_moins_les_deux_postes_de_couts(tmp_path):
    """Vérité arithmétique : 100 moins 10 moins 20 fait 70, puis 80 moins 25 moins 25 fait 30,
    soit une baisse de 57,142857 %."""
    resultats = variation(charger(_fichier_bdc(tmp_path / "mini.csv")))
    ligne = resultats.iloc[0]
    assert ligne["reference"] == pytest.approx(70.0)
    assert ligne["scenario"] == pytest.approx(30.0)
    assert ligne["variation_pct"] == pytest.approx(100 * (30 / 70 - 1))
    assert ligne["publie_pct"] == PUBLIES["Refined oil products"]["resultat_net_pct"]


def test_un_scenario_absent_est_refuse_plutot_que_devine(tmp_path):
    with pytest.raises(ValueError, match="scénario absent"):
        variation(charger(_fichier_bdc(tmp_path / "mini.csv")), scenario="Net-zero 2050 (1.5°C)")
