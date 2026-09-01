"""Les trois analyses qui vont au-delà de l'exemple : la mécanique, la carte, l'inversion."""

from pathlib import Path

import numpy as np
import pytest

from scc.exemple import MAJORATIONS
from scc.merton import (
    CHOC_RAFFINAGE,
    courbe_levier,
    levier_requis,
    probabilite_de_defaut,
    ratio_apres_choc,
)
from scc.scenarios import PUBLIES, charger, trajectoire, variation
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
        assert 0.13 < depart < 0.20


def test_le_levier_apres_choc_n_est_pas_plafonne_a_un():
    """Le test qui manquait, et sans lequel un plafond invisible a faussé tout le tableau 5.4.

    Une première version ramenait le levier d'après choc à un dès qu'il le dépassait. Comme le choc
    de raffinage divise le levier par 0,289, tout emprunteur au-delà de 28,9 % d'endettement était
    plafonné, donc TOUS les leviers publiés l'étaient. Le défaut est invisible à l'aller-retour de
    l'inversion, qui reste cohérent avec lui-même, et invisible à une borne sur le résultat.

    Ce qui le trahit est qu'un plafond écrase deux emprunteurs différents sur la même valeur : une
    fois plafonnés, 40 % et 60 % d'endettement donnent la MÊME probabilité après choc. Le test exige
    donc qu'ils en donnent deux différentes.
    """
    choc = 0.711
    assert 0.40 / (1 - choc) > 1.0 and 0.60 / (1 - choc) > 1.0, "les deux doivent dépasser le plafond"

    def pd_apres(levier):
        # la probabilité après choc se relit depuis le rapport, qui est ce que le module publie
        return ratio_apres_choc(levier, choc, 0.25) * probabilite_de_defaut(levier, 0.25)

    faible, fort = pd_apres(0.40), pd_apres(0.60)
    assert faible < fort, "un emprunteur plus endetté doit rester plus risqué après le choc"
    assert fort - faible > 0.01, "un plafond les rendrait égaux"
    assert fort < 1.0


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


def _fichier_bdc(chemin, secteurs=("Refined oil products",), annees=(2050,)):
    """Un fichier au format de la Banque du Canada : bloc d'en-tête, puis les observations."""
    lignes = ['"TERMS AND CONDITIONS"', '"https://www.bankofcanada.ca/terms/"', "",
              '"OBSERVATIONS"',
              '"k","CL_GEOGRAPHY","CL_SECTOR","CL_VARIABLE","CL_UNIT","CL_SCENARIO","CL_YEAR",'
              '"CL_VALUE"']
    k = 0
    for secteur in secteurs:
        for annee in annees:
            for scenario, (revenu, direct, indirect) in {
                    "Baseline (2019 policies)": (100.0, 10.0, 20.0),
                    "Below 2°C immediate": (80.0, 25.0, 25.0)}.items():
                for variable, valeur in [("Revenue", revenu), ("Direct emissions costs", direct),
                                         ("Indirect costs", indirect)]:
                    k += 1
                    lignes.append(f'"{k}","Canada","{secteur}","{variable}","10 BN US$2014",'
                                  f'"{scenario}","{annee}","{valeur}"')
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
    assert ligne["reference_10_milliards_usd_2014"] == pytest.approx(70.0)
    assert ligne["scenario_10_milliards_usd_2014"] == pytest.approx(30.0)
    assert ligne["variation_pct"] == pytest.approx(100 * (30 / 70 - 1))
    assert ligne["publie_pct"] == PUBLIES["Refined oil products"]["resultat_net_pct"]


def test_un_scenario_absent_est_refuse_plutot_que_devine(tmp_path):
    with pytest.raises(ValueError, match="scénario absent"):
        variation(charger(_fichier_bdc(tmp_path / "mini.csv")), scenario="Net-zero 2050 (1.5°C)")


def test_un_secteur_agrege_est_marque_plutot_que_compte_deux_fois(tmp_path):
    """« Pétrole et gaz » est la somme de « Pétrole » et de « Gaz », donc il recouvre deux lignes.

    Sans la marque, une figure qui aligne les trois barres compte deux fois la même activité, et le
    lecteur qui somme ou qui pondère les secteurs se trompe du double sur l'activité pétrolière.
    """
    fichier = _fichier_bdc(tmp_path / "trois.csv", secteurs=("Oil", "Gas", "Oil & Gas"))
    resultats = variation(charger(fichier))
    marques = set(resultats.loc[resultats["agregat"], "secteur"])
    assert marques == {"Pétrole et gaz"}
    assert not resultats.loc[resultats["secteur"].isin(["Pétrole", "Gaz"]), "agregat"].any()


def test_la_trajectoire_rend_une_ligne_par_annee_et_une_colonne_par_scenario(tmp_path):
    """Le résultat net année par année : 100 moins 10 moins 20 fait 70, sur chacune des trois."""
    fichier = _fichier_bdc(tmp_path / "annees.csv", annees=(2030, 2040, 2050))
    net = trajectoire(charger(fichier), "Refined oil products")
    assert list(net.index) == [2030, 2040, 2050]
    assert set(net.columns) == {"Baseline (2019 policies)", "Below 2°C immediate"}
    assert net["Baseline (2019 policies)"].tolist() == pytest.approx([70.0, 70.0, 70.0])
    assert net["Below 2°C immediate"].tolist() == pytest.approx([30.0, 30.0, 30.0])


@pytest.mark.skipif(not Path("data/raw/scenarios_bdc.csv").exists(),
                    reason="exige `scc fetch` : le fichier public n'est jamais commité")
def test_le_choc_par_defaut_est_l_arrondi_de_la_valeur_mesuree():
    """La constante 0,711 est un arrondi, pas une lecture : ce test l'attache à sa source.

    Sans lui, une révision du fichier de la Banque du Canada déplacerait
    `results/secteurs_resultat_net.csv` pendant que l'inversion de Merton continuerait de tourner
    sur 0,711, sans que rien ne le signale.
    """
    table = charger("data/raw/scenarios_bdc.csv")
    raffinage = variation(table)
    mesure = float(raffinage.loc[raffinage["secteur"].eq("Produits pétroliers raffinés"),
                                 "variation_pct"].iloc[0])
    assert -mesure / 100.0 == pytest.approx(CHOC_RAFFINAGE, abs=1e-3)
