"""L'exemple officiel du BSIF, retrouvé chiffre par chiffre. C'est le test qui porte le dépôt."""

import numpy as np
import pytest

from scc import exemple as ex
from scc.scse import (
    Exposition,
    conditionnelles,
    ecl_climatique,
    ecl_de_reference,
    inconditionnelles,
    lgd_frye_jacobs,
    logit,
    pd_climatiques,
    seau_qualite,
    sigmoide,
)


@pytest.fixture
def exposition():
    return ex.exposition()


def test_les_trois_pertes_de_reference_sont_celles_du_bsif(exposition):
    """Avant tout climat : la perte attendue comptable, scénario par scénario."""
    calcule = ecl_de_reference(exposition)
    for nom, publie in ex.ECL_REFERENCE.items():
        assert calcule["par_scenario"][nom] == pytest.approx(publie, abs=1e-8)
    assert calcule["ponderee"] == pytest.approx(ex.ECL_REFERENCE_PONDEREE, abs=1e-8)


def test_le_seau_de_qualite_se_deduit_de_la_premiere_annee(exposition):
    """La probabilité pondérée de 2024 vaut 3,55 %, ce qui tombe dans le seau 4."""
    calcule = ecl_de_reference(exposition)
    assert calcule["pd_ponderee"] == pytest.approx(ex.PD_PONDEREE_PREMIERE_ANNEE, abs=1e-15)
    assert calcule["seau"] == ex.SEAU_ATTENDU


def test_les_bornes_des_seaux_sont_incluses_en_bas_et_exclues_en_haut():
    """Le détail qui décide d'un classement : 0,25 % appartient au seau 3, pas au seau 2."""
    assert seau_qualite(0.0025) == 3
    assert seau_qualite(0.0024999) == 2
    assert seau_qualite(0.0) == 1
    assert seau_qualite(0.99) == 6


@pytest.mark.parametrize("horizon", ex.HORIZONS)
def test_les_quatre_pertes_climatiques_sont_celles_du_bsif(exposition, horizon):
    """Les quatre horizons de l'exercice, chacun avec ses six majorations."""
    calcule = ecl_climatique(exposition, ex.majorations_de(horizon, 6))["ponderee"]
    assert calcule == pytest.approx(ex.ECL_PAR_HORIZON[horizon], abs=1e-6)


def test_le_detail_de_l_horizon_2045_est_retrouve_annee_par_annee(exposition):
    """Pas seulement le total : les six probabilités et les six pertes en cas de défaut."""
    detail = ecl_climatique(exposition, ex.majorations_de(2045, 6))["detail"]["pessimiste"]
    assert np.allclose(detail["pd"], ex.PD_CLIMATIQUES_2045_PESSIMISTE, atol=1e-15, rtol=0)
    assert np.allclose(detail["lgd"], ex.LGD_CLIMATIQUES_2045_PESSIMISTE, atol=1e-14, rtol=0)


def test_les_trois_totaux_de_l_horizon_2045_sont_retrouves(exposition):
    calcule = ecl_climatique(exposition, ex.majorations_de(2045, 6))["par_scenario"]
    for nom, publie in ex.ECL_CLIMATIQUE_2045.items():
        assert calcule[nom] == pytest.approx(publie, abs=1e-6)


def test_le_conditionnel_et_l_inconditionnel_sont_reciproques():
    """Aller et retour : la transformation ne doit rien perdre."""
    depart = np.array([0.04, 0.035, 0.03, 0.025, 0.02, 0.015])
    cpd, _ = conditionnelles(depart)
    assert np.allclose(inconditionnelles(cpd), depart, atol=1e-15, rtol=0)


def test_la_conditionnelle_de_la_deuxieme_annee_se_calcule_a_la_main():
    """3,5 % d'inconditionnelle sur une survie de 96 % donne 3,645833... % de conditionnelle."""
    cpd, survies = conditionnelles([0.04, 0.035])
    assert cpd[0] == pytest.approx(0.04)
    assert survies[0] == pytest.approx(0.96)
    assert cpd[1] == pytest.approx(0.035 / 0.96, abs=1e-15)


def test_le_logit_et_la_sigmoide_sont_reciproques():
    p = np.array([1e-6, 0.001, 0.04, 0.5, 0.9])
    assert np.allclose(sigmoide(logit(p)), p, atol=1e-15, rtol=1e-12)


def test_une_majoration_nulle_ne_change_rien(exposition):
    """Le contrôle le plus simple, et celui qui attrape le plus de fautes de signe."""
    reference = ecl_de_reference(exposition)["ponderee"]
    sans_effet = ecl_climatique(exposition, np.zeros(6))["ponderee"]
    assert sans_effet == pytest.approx(reference, abs=1e-8)


def test_une_majoration_positive_augmente_toujours_la_perte(exposition):
    reference = ecl_de_reference(exposition)["ponderee"]
    for horizon in ex.HORIZONS:
        assert ecl_climatique(exposition, ex.majorations_de(horizon, 6))["ponderee"] > reference


def test_frye_jacobs_laisse_la_perte_intacte_quand_la_probabilite_ne_bouge_pas():
    """La relation doit être l'identité à probabilité inchangée, sinon elle décale tout."""
    p = np.array([0.04, 0.02, 0.01])
    lgd = np.array([0.8, 0.6, 0.45])
    assert np.allclose(lgd_frye_jacobs(p, p, lgd), lgd, atol=1e-12, rtol=0)


def test_frye_jacobs_fait_monter_la_perte_quand_la_probabilite_monte():
    """Le sens de la relation : les défaillances se concentrent dans les mauvaises années."""
    p = np.array([0.04])
    lgd = np.array([0.8])
    montee = lgd_frye_jacobs(p * 1.5, p, lgd)
    assert montee[0] > lgd[0]
    assert montee[0] < 1.0


def test_la_majoration_se_prolonge_au_dela_de_la_derniere_annee_publiee():
    """Les majorations s'arrêtent en 2050 ; une exposition plus longue reprend la dernière."""
    longues = ex.majorations_de(2045, 10)
    assert longues[4] == pytest.approx(ex.MAJORATIONS[2050])
    assert np.all(longues[4:] == ex.MAJORATIONS[2050])


def test_les_poids_des_scenarios_doivent_sommer_a_un():
    with pytest.raises(ValueError, match="sommer à un"):
        Exposition(pd_par_scenario={"a": np.array([0.01])}, lgd=np.array([0.5]),
                   ead=np.array([1.0]), poids={"a": 0.9})


def test_il_faut_une_majoration_par_annee(exposition):
    with pytest.raises(ValueError, match="une majoration par année"):
        ecl_climatique(exposition, np.zeros(3))


def test_les_probabilites_climatiques_restent_des_probabilites():
    """Le passage par le logit garantit l'intervalle : une majoration énorme ne doit pas déborder."""
    resultat = pd_climatiques([0.4, 0.3, 0.2], [10.0, 10.0, 10.0])
    assert np.all(resultat > 0.0) and np.all(resultat < 1.0)
    assert resultat.sum() < 1.0
