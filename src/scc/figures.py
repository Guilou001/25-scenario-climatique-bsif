"""Six figures, chacune portant un des six verdicts du dépôt.

Toutes s'appuient sur `gvf.style` et `gvf.figures`, la couche partagée du portefeuille : la palette,
la virgule décimale des axes et l'écriture simultanée en PNG et en PDF vectoriel n'ont pas à être
réécrites ici.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from gvf.figures import cascade
from gvf.style import GRIS, OKABE_ITO, appliquer, enregistrer, formateur, fr

from . import exemple as ex
from .merton import courbe_levier
from .scse import SEAUX, ecl_climatique, ecl_de_reference
from .sensibilite import ECHEANCES, hausse_de_probabilite, milieu_de_seau

DEST = Path("results/figures")


def fig_exemple(dest: Path = DEST) -> dict:
    """La perte attendue de l'exemple officiel, calculée contre publiée, aux quatre horizons.

    C'est la figure de la vérification : si une barre calculée s'écartait de son point publié, elle
    se verrait. Aucune ne s'en écarte, et c'est le titre qui porte l'écart, sous la forme du seuil
    décimal qui le borne, pour que l'absence d'écart visible ne passe pas pour une figure vide.
    """
    appliquer()
    exposition = ex.exposition()
    reference = ecl_de_reference(exposition)["ponderee"]
    horizons = list(ex.HORIZONS)
    calcules = [ecl_climatique(exposition, ex.majorations_de(h, 6))["ponderee"] for h in horizons]
    publies = [ex.ECL_PAR_HORIZON[h] for h in horizons]
    ecart = max(abs(c - p) for c, p in zip(calcules, publies, strict=True))

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    positions = np.arange(len(horizons))
    # les barres partent de la perte de référence : leur hauteur est donc la hausse elle-même, et
    # non une valeur absolue posée sur un axe tronqué, qui exagérerait l'écart
    ax.bar(positions, [c - reference for c in calcules], bottom=reference, width=0.55,
           color=OKABE_ITO[0], label="recalculé par ce dépôt")
    ax.scatter(positions, publies, s=70, zorder=5, color=OKABE_ITO[3], marker="D",
               label="publié par le BSIF")
    ax.axhline(reference, color=GRIS, linestyle="--", linewidth=1.2)
    # sous la ligne et non au-dessus : au-dessus, le texte traverse la première barre
    ax.annotate(f"perte attendue avant climat : {fr(reference, 0)} $", (-0.45, reference),
                xytext=(0, -13), textcoords="offset points", ha="left", va="top", fontsize=9,
                color=GRIS)
    for x, c in zip(positions, calcules, strict=True):
        ax.annotate(f"+{fr(100 * (c / reference - 1), 2)} %", (x, c), xytext=(0, 5),
                    textcoords="offset points", ha="center", fontsize=9, color=GRIS)
    ax.set_xticks(positions, [str(h) for h in horizons])
    ax.set_xlabel("Horizon de l'exercice")
    ax.set_ylabel("Perte de crédit attendue sur la durée de vie\n(dollars, pondérée des scénarios)")
    ax.yaxis.set_major_formatter(formateur(0))
    ax.set_ylim(reference - 0.14 * (max(calcules) - reference),
                reference + 1.35 * (max(calcules) - reference))
    ax.legend(loc="upper left")
    # le seuil du titre se déduit de l'écart mesuré plutôt que d'être écrit en dur : si l'écart
    # grandissait un jour, le titre le dirait au lieu de continuer à promettre le milliardième
    seuils = ((1e-12, "billionième"), (1e-9, "milliardième"), (1e-6, "millionième"),
              (1e-3, "millième"))
    nom_du_seuil = next((nom for seuil, nom in seuils if ecart < seuil), None)
    accord = (f"retrouvées à moins d'un {nom_du_seuil} de dollar près" if nom_du_seuil
              else f"écartées de {fr(ecart, 6)} dollar au plus")
    ax.set_title(f"Les quatre pertes attendues de l'exemple du BSIF, {accord}")
    enregistrer(fig, dest, "exemple_bsif")
    plt.close(fig)
    return {"ecart_max_dollars": ecart, "reference": reference,
            "hausses_pct": [100 * (c / reference - 1) for c in calcules]}


def fig_mecanique(dest: Path = DEST) -> dict:
    """Pourquoi la majoration frappe les bons emprunteurs plus fort, en proportion.

    La majoration s'ajoute au logit, donc multiplie la cote de défaut. Sur une petite probabilité la
    cote vaut presque la probabilité, et la hausse relative atteint son plafond ; sur une grande
    probabilité la cote est bien plus grande, et la même opération déplace beaucoup moins.
    """
    appliquer()
    majoration = ex.MAJORATIONS[2046]
    grille = np.logspace(-4, np.log10(0.6), 400)
    hausses = hausse_de_probabilite(grille, majoration)
    plafond = 100.0 * (np.exp(majoration) - 1.0)

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.plot(100 * grille, hausses, color=OKABE_ITO[0], linewidth=2.0)
    ax.axhline(plafond, color=GRIS, linestyle="--", linewidth=1.1)
    ax.annotate(f"plafond quand la probabilité tend vers zéro : {fr(plafond, 2)} %",
                (0.011, plafond), xytext=(0, -14), textcoords="offset points", fontsize=9,
                color=GRIS)
    for numero, bas, _ in SEAUX[1:]:
        ax.axvline(100 * bas, color=GRIS, linewidth=0.6, alpha=0.5)
        ax.annotate(f"seau {numero}", (100 * bas, 2.0), xytext=(3, 0), textcoords="offset points",
                    fontsize=8, color=GRIS)
    for numero, _, _ in SEAUX:
        p = milieu_de_seau(numero)
        ax.scatter([100 * p], [hausse_de_probabilite(p, majoration)], s=45, zorder=5,
                   color=OKABE_ITO[3])
    ax.set_xscale("log")
    ax.set_xlabel("Probabilité de défaut avant majoration (%, échelle logarithmique)")
    ax.set_ylabel("Hausse de la probabilité de défaut\n(% de sa valeur initiale)")
    ax.set_ylim(0, plafond * 1.18)
    ax.set_title("La même majoration fait monter en proportion la probabilité d'un bon emprunteur "
                 "plus que celle d'un mauvais")
    enregistrer(fig, dest, "mecanique_logit")
    plt.close(fig)
    return {"plafond_pct": plafond,
            "par_seau": {n: float(hausse_de_probabilite(milieu_de_seau(n), majoration))
                         for n, _, _ in SEAUX}}


def fig_carte(table, dest: Path = DEST) -> dict:
    """La hausse de la perte attendue par seau de qualité et par échéance.

    Une ligne par seau. Le croisement des lignes est le résultat : à une échéance courte les six
    seaux se tiennent, à vingt ans ils s'écartent d'un facteur six.
    """
    appliquer()
    colonnes = [f"{a} ans" for a in ECHEANCES]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for rang, (numero, ligne) in enumerate(table.iterrows()):
        ax.plot(ECHEANCES, [ligne[c] for c in colonnes], marker="o", markersize=4,
                color=OKABE_ITO[rang % len(OKABE_ITO)],
                label=f"seau {numero} : PD {fr(100 * ligne['pd_conditionnelle'], 2)} %")
    ax.set_xlabel("Échéance résiduelle de l'exposition, en années")
    ax.set_ylabel("Hausse de la perte de crédit attendue\n(% de la perte de référence)")
    ax.set_xticks(list(ECHEANCES))
    ax.yaxis.set_major_formatter(formateur(0, " %"))
    ax.legend(ncol=2, loc="lower left")
    rapport = table[colonnes[-1]].iloc[0] / table[colonnes[-1]].iloc[-1]
    ax.set_title("À vingt ans, la même majoration coûte "
                 f"{fr(rapport, 1)} fois plus au meilleur seau qu'au pire")
    enregistrer(fig, dest, "carte_sensibilite")
    plt.close(fig)
    return {"rapport_20_ans": float(rapport)}


def fig_secteurs(variations, dest: Path = DEST) -> dict:
    """Le résultat net par secteur en 2050, recalculé, avec les deux valeurs publiées en regard.

    Les lignes marquées `agregat` sont retirées. « Pétrole et gaz » est la somme de « Pétrole » et
    de « Gaz », au dernier chiffre publié près, et les trois côte à côte feraient compter deux fois
    la même activité.
    """
    appliquer()
    ecartes = []
    if "agregat" in variations.columns:
        ecartes = list(variations.loc[variations["agregat"], "secteur"])
        variations = variations[~variations["agregat"]]
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    positions = np.arange(len(variations))
    couleurs = [OKABE_ITO[3] if v < 0 else OKABE_ITO[2] for v in variations["variation_pct"]]
    ax.barh(positions, variations["variation_pct"], color=couleurs, height=0.62)
    connus = variations["publie_pct"].notna()
    ax.scatter(variations.loc[connus, "publie_pct"], positions[connus.to_numpy()], s=80,
               marker="D", color=OKABE_ITO[0], zorder=5,
               label="publié page 32 du PDF du rapport (folio 31)")
    for i, (_, ligne) in enumerate(variations.iterrows()):
        if np.isfinite(ligne["publie_pct"]):
            # à gauche du plus à gauche des deux repères, sinon le texte passe sur le losange
            ax.annotate(f"écart {fr(ligne['ecart_points'], 1)} point",
                        (min(ligne["variation_pct"], ligne["publie_pct"]), i), xytext=(-10, 0),
                        textcoords="offset points", ha="right", va="center", fontsize=8.5,
                        color=GRIS)
    ax.axvline(0, color=GRIS, linewidth=0.9)
    ax.set_yticks(positions, variations["secteur"])
    ax.set_xlabel("Variation du résultat net en 2050 contre le scénario de référence (%)")
    ax.xaxis.set_major_formatter(formateur(0))
    # en haut à gauche : les secteurs les moins touchés sont en haut, donc ce coin est vide
    ax.legend(loc="upper left")
    ax.set_title("Le premier maillon du rapport se refait depuis le fichier public")
    enregistrer(fig, dest, "secteurs_2050")
    plt.close(fig)
    return {"secteurs": int(len(variations)), "agregats_ecartes": ecartes}


def fig_cascade(net, dest: Path = DEST) -> dict:
    """La décomposition du résultat net du raffinage, scénario de référence puis transition.

    `net` est un dictionnaire de deux lignes, référence et scénario, portant les trois postes. Les
    valeurs du fichier sont en dizaines de milliards de dollars de 2014 : elles sont converties en
    milliards, seule unité dans laquelle un lecteur reconnaît un ordre de grandeur.

    Les deux volets partagent leurs limites verticales, mais elles sont posées APRÈS les deux
    cascades et non par `sharey`. Avec `sharey`, le second volet écrase les limites du premier, et
    ses barres sortent du cadre sans que rien ne le signale.
    """
    appliquer()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    cumuls = {}
    for ax, (titre, ligne) in zip(axes, net.items(), strict=True):
        cumuls[titre] = cascade(
            ax, ["Coûts directs d'émission", "Coûts indirects"],
            [-10 * ligne["Direct emissions costs"], -10 * ligne["Indirect costs"]],
            depart=10 * ligne["Revenue"], total="Résultat net", decimales=2)
        # sans cette étiquette, les produits ne se lisent nulle part : la cascade en part, mais
        # aucune barre ne les porte, et le mode d'emploi de la figure les commente pourtant
        ax.annotate(f"produits : {fr(cumuls[titre][0], 2)}", (0, cumuls[titre][0]),
                    xytext=(0, 13), textcoords="offset points", ha="center", va="bottom",
                    fontsize=8.5, color=GRIS)
        ax.set_title(titre)
        ax.yaxis.set_major_formatter(formateur(0))

    tous = np.concatenate(list(cumuls.values()))
    plancher, plafond = min(0.0, float(tous.min())), float(tous.max())
    for ax in axes:
        ax.set_ylim(plancher, plafond * 1.16)
    axes[0].set_ylabel("Milliards de dollars US de 2014")
    fig.suptitle("Produits pétroliers raffinés au Canada en 2050 : d'où vient la baisse")
    enregistrer(fig, dest, "cascade_raffinage")
    plt.close(fig)
    return {titre: {"produits": float(v[0]), "resultat_net": float(v[-1])}
            for titre, v in cumuls.items()}


def fig_merton(dest: Path = DEST) -> dict:
    """Le levier et la probabilité de défaut de départ qu'il faudrait pour retrouver +450 %.

    Deux axes, parce que les deux grandeurs ne se lisent pas dans la même unité. Le levier est à
    gauche et la probabilité de défaut de départ à droite, celle qui se compare à une notation.
    """
    appliquer()
    volatilites, leviers, depart = courbe_levier()
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.plot(100 * volatilites, 100 * leviers, color=OKABE_ITO[0], linewidth=2.0,
            label="levier requis (dette sur actif)")
    ax.set_xlabel("Volatilité de la valeur d'actif de l'emprunteur (% par an)")
    ax.set_ylabel("Levier requis (%)")
    ax.yaxis.set_major_formatter(formateur(0))

    second = ax.twinx()
    second.plot(100 * volatilites, 100 * depart, color=OKABE_ITO[1], linewidth=2.0,
                label="probabilité de défaut de départ")
    second.set_ylabel("Probabilité de défaut à cinq ans, avant le choc (%)")
    second.grid(False)
    second.set_ylim(0, max(100 * np.nanmax(depart) * 1.25, 1.0))
    second.yaxis.set_major_formatter(formateur(0))

    # la bande des volatilités d'actif ordinaires d'une entreprise cotée : hors d'elle, à 40 % et
    # plus, la réponse s'effondre, et le dire fait partie du résultat
    # la comparaison est tolérante : la grille est construite par `linspace`, dont la volatilité de
    # 30 % vaut 0,300 000 000 000 000 04, et un test strict l'exclurait de la bande que `axvspan`
    # dessine pourtant jusqu'à 30
    usuelle = (volatilites >= 0.15 - 1e-9) & (volatilites <= 0.30 + 1e-9)
    ax.axvspan(15, 30, color=GRIS, alpha=0.08, linewidth=0)
    bas, haut = 100 * depart[usuelle].min(), 100 * depart[usuelle].max()
    second.annotate(f"plage usuelle de volatilité d'actif :\nprobabilité de départ de "
                    f"{fr(bas, 1)} à {fr(haut, 1)} %", (22.5, haut), xytext=(0, 14),
                    textcoords="offset points", ha="center", fontsize=9, color=GRIS)

    lignes = ax.get_lines() + second.get_lines()
    ax.legend(lignes, [ligne.get_label() for ligne in lignes], loc="lower left")
    fini = np.isfinite(depart)
    # le titre se déduit des données plutôt que d'être écrit à la main : une version figée annonçait
    # « une fois sur dix » et a survécu à une correction qui déplaçait la plage. L'arrondi est au
    # demi et non à l'entier : à l'entier, 5,51 devient 6, et le titre fait paraître l'emprunteur
    # moins fragile que le corps du texte ne le dit
    sur = round(2.0 / (haut / 100.0)) / 2.0
    ax.set_title("Pour que la probabilité de défaut quintuple, il faut un emprunteur qui défaille "
                 f"déjà une fois sur {fr(sur, 1)}")
    enregistrer(fig, dest, "inversion_merton")
    plt.close(fig)
    return {"pd_depart_min_pct": float(100 * np.nanmin(depart[fini])),
            "pd_depart_max_pct": float(100 * np.nanmax(depart[fini])),
            "plage_usuelle_pct": (float(bas), float(haut))}
