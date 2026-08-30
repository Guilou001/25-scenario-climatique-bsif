"""Les commandes du dépôt. Chaque verdict du README sort d'une de ces commandes, dans `results/`."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import typer

from . import donnees
from . import exemple as ex
from .merton import courbe_levier, levier_requis, probabilite_de_defaut
from .scse import ecl_climatique, ecl_de_reference

app = typer.Typer(add_completion=False, help=__doc__)
RESULTATS = Path("results")


def _ecrire(table: pd.DataFrame, nom: str) -> Path:
    RESULTATS.mkdir(parents=True, exist_ok=True)
    chemin = RESULTATS / nom
    table.to_csv(chemin, index=True)
    typer.echo(f"écrit {chemin}")
    return chemin


@app.command()
def fetch():
    """Télécharger les quatre fichiers publics dans `data/raw`."""
    for nom, taille in donnees.fetch().items():
        typer.echo(f"{nom:26s} {taille:>12,} octets".replace(",", " "))


@app.command()
def verifier():
    """Comparer les constantes de `exemple.py` au classeur du BSIF téléchargé.

    Prouve que la vérité connue du dépôt est bien celle du régulateur, et non une transcription.
    """
    lu = ex.lire_exemple(donnees.chemin("scse_instructions.xlsx"))
    controles = [
        ("probabilités de défaut, trois scénarios",
         max(float(np.abs(lu["pd_inconditionnelles"][n] - ex.PD_INCONDITIONNELLES[n]).max())
             for n in ex.SCENARIOS)),
        ("perte en cas de défaut", float(np.abs(lu["lgd"] - ex.LGD).max())),
        ("exposition", float(np.abs(lu["ead"] - ex.EAD).max())),
        ("perte attendue de référence, pondérée",
         abs(lu["ecl_reference_ponderee"] - ex.ECL_REFERENCE_PONDEREE)),
        ("probabilités climatiques 2045",
         float(np.abs(lu["pd_climatiques_2045_pessimiste"]
                      - ex.PD_CLIMATIQUES_2045_PESSIMISTE).max())),
        ("pertes en cas de défaut climatiques 2045",
         float(np.abs(lu["lgd_climatiques_2045_pessimiste"]
                      - ex.LGD_CLIMATIQUES_2045_PESSIMISTE).max())),
        ("perte attendue climatique 2045, trois scénarios",
         max(abs(lu["ecl_climatique_2045"][n] - ex.ECL_CLIMATIQUE_2045[n]) for n in ex.SCENARIOS)),
        ("majorations, 21 années",
         max(abs(lu["majorations"][a] - ex.MAJORATIONS[a]) for a in ex.MAJORATIONS)),
    ]
    for nom, ecart in controles:
        etat = "identique" if ecart == 0.0 else f"écart {ecart:.3e}"
        typer.echo(f"{nom:44s} {etat}")


@app.command()
def module():
    """Recalculer l'exemple officiel et écrire les écarts au publié."""
    exposition = ex.exposition()
    reference = ecl_de_reference(exposition)
    lignes = [{"grandeur": f"perte de référence, {nom}", "calcule": v,
               "publie": ex.ECL_REFERENCE[nom], "ecart": v - ex.ECL_REFERENCE[nom]}
              for nom, v in reference["par_scenario"].items()]
    lignes.append({"grandeur": "perte de référence, pondérée", "calcule": reference["ponderee"],
                   "publie": ex.ECL_REFERENCE_PONDEREE,
                   "ecart": reference["ponderee"] - ex.ECL_REFERENCE_PONDEREE})
    for horizon in ex.HORIZONS:
        v = ecl_climatique(exposition, ex.majorations_de(horizon, 6))["ponderee"]
        lignes.append({"grandeur": f"perte climatique, horizon {horizon}", "calcule": v,
                       "publie": ex.ECL_PAR_HORIZON[horizon],
                       "ecart": v - ex.ECL_PAR_HORIZON[horizon]})
    table = pd.DataFrame(lignes).set_index("grandeur")
    # la hausse ne se compare qu'à la perte pondérée : la rapporter pour un scénario pris seul
    # confronterait deux grandeurs différentes
    climatique = table.index.str.startswith("perte climatique")
    table["hausse_pct"] = np.where(climatique,
                                   100.0 * (table["calcule"] / reference["ponderee"] - 1.0), np.nan)
    _ecrire(table, "exemple_bsif.csv")
    typer.echo(f"écart maximal en dollars : {table['ecart'].abs().max():.3e}")
    typer.echo(f"seau de qualité de crédit : {reference['seau']} (attendu {ex.SEAU_ATTENDU})")


@app.command()
def sensibilite(horizon: int = 2045):
    """La carte de la hausse de perte attendue, par seau de qualité et par échéance."""
    from .sensibilite import carte, par_horizon

    table = carte(horizon)
    _ecrire(table, "carte_sensibilite.csv")
    _ecrire(par_horizon(), "hausse_par_horizon.csv")
    colonne = table.columns[-1]
    typer.echo(f"à {colonne}, seau 1 monte de {table[colonne].iloc[0]:.2f} % et seau 6 de "
               f"{table[colonne].iloc[-1]:.2f} %, soit un rapport de "
               f"{table[colonne].iloc[0] / table[colonne].iloc[-1]:.2f}")


@app.command()
def secteurs(annee: int = 2050, scenario: str = "Below 2°C immediate"):
    """Le résultat net par secteur depuis le fichier de la Banque du Canada, contre le publié."""
    from .scenarios import charger, variation

    table = charger(donnees.chemin("scenarios_bdc.csv"))
    resultats = variation(table, annee=annee, scenario=scenario)
    _ecrire(resultats.reset_index(drop=True).set_index("secteur"), "secteurs_resultat_net.csv")
    for _, ligne in resultats[resultats["publie_pct"].notna()].iterrows():
        typer.echo(f"{ligne['secteur']:32s} calculé {ligne['variation_pct']:7.2f} % "
                   f"publié {ligne['publie_pct']:6.1f} % écart {ligne['ecart_points']:5.2f} point")


@app.command()
def merton(horizon: float = 5.0):
    """L'inversion : quel emprunteur faudrait-il pour que la probabilité de défaut quintuple."""
    volatilites, leviers, depart = courbe_levier(horizon=horizon)
    table = pd.DataFrame({"volatilite": volatilites, "levier_requis": leviers,
                          "pd_depart": depart}).set_index("volatilite")
    _ecrire(table, "inversion_merton.csv")

    lignes = []
    for t in (1.0, 2.0, 3.0, 5.0, 7.0, 10.0):
        for vol in (0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
            levier = levier_requis(volatilite=vol, horizon=t)
            lignes.append({"horizon": t, "volatilite": vol, "levier": levier,
                           "pd_depart_pct": 100 * probabilite_de_defaut(levier, vol, t)
                           if np.isfinite(levier) else np.nan})
    robustesse = pd.DataFrame(lignes).pivot(index="horizon", columns="volatilite",
                                            values="pd_depart_pct")
    _ecrire(robustesse, "inversion_merton_robustesse.csv")
    central = robustesse.loc[:, [0.15, 0.20, 0.25, 0.30]]
    typer.echo(f"probabilité de défaut de départ requise, volatilité de 15 à 30 % : "
               f"{central.min().min():.2f} % à {central.max().max():.2f} %")


@app.command()
def figures():
    """Les six figures, en PNG pour le README et en PDF vectoriel pour le rapport."""
    from . import figures as fig
    from .scenarios import charger, resultat_net, variation
    from .sensibilite import carte

    typer.echo(f"exemple  : {fig.fig_exemple()}")
    typer.echo(f"mécanique: {fig.fig_mecanique()}")
    typer.echo(f"carte    : {fig.fig_carte(carte())}")
    typer.echo(f"merton   : {fig.fig_merton()}")

    table = charger(donnees.chemin("scenarios_bdc.csv"))
    typer.echo(f"secteurs : {fig.fig_secteurs(variation(table))}")
    net = resultat_net(table)
    raffinage = {
        "Scénario de référence (politiques de 2019)":
            net.loc[("Refined oil products", "Baseline (2019 policies)")],
        "Sous 2 °C, action immédiate":
            net.loc[("Refined oil products", "Below 2°C immediate")],
    }
    typer.echo(f"cascade  : {fig.fig_cascade(raffinage)}")


@app.command()
def tout():
    """Toutes les commandes de calcul, dans l'ordre. Exige `scc fetch` au préalable."""
    module()
    sensibilite()
    secteurs()
    merton()
    figures()


if __name__ == "__main__":
    app()
