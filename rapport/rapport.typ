#set document(title: "Recalculer le scénario climatique demandé par le BSIF", author: "Guillaume Vaudescal")
#set page(
  paper: "a4",
  margin: (x: 2.2cm, y: 2.4cm),
  numbering: "1 / 1",
  footer: context [
    #set text(size: 8pt, fill: luma(90))
    #grid(columns: (1fr, auto), align: (left, right),
      [scenario-climatique], [#counter(page).display("1 / 1", both: true)])
  ],
)
#set text(font: ("Helvetica", "Arial", "DejaVu Sans"), size: 10pt, lang: "fr")
#set par(justify: true, leading: 0.68em, spacing: 1.1em)
#set heading(numbering: none)
#show heading.where(level: 2): it => block(above: 1.6em, below: 0.8em, text(size: 13pt, it))
#show heading.where(level: 3): it => block(above: 1.2em, below: 0.6em, text(size: 11pt, it))
#show raw.where(block: true): it => block(
  fill: luma(246), inset: 8pt, radius: 3pt, width: 100%, text(size: 8.5pt, it))
#show raw.where(block: false): it => text(size: 9pt, fill: rgb("#1a3f66"), it)
#show quote.where(block: true): it => block(
  inset: (left: 10pt), stroke: (left: 1.5pt + luma(180)),
  text(style: "italic", fill: luma(45), it.body))
// la table NE DOIT PAS être enfermée dans un par() : Typst 0.15 la supprime alors
// entièrement, sans erreur. Le réglage se pose donc dans la portée du bloc.
#show table: it => block(above: 1.1em, below: 1.1em,
  [#set par(justify: false); #text(size: 8.8pt, it)])
#show figure: it => block(above: 1.4em, below: 1.4em, it)
#show figure.caption: it => text(size: 8.5pt, fill: luma(70), it)
#show link: it => text(fill: rgb("#0072B2"), it)

#align(center)[
  #block(width: 100%)[
    #text(size: 18pt, weight: "bold")[Recalculer le scénario climatique demandé par le BSIF]
    #v(0.6em)
    #text(size: 10pt, fill: luma(70))[Guillaume Vaudescal · 2026-09-04 · #link("https://github.com/Guilou001/25-scenario-climatique-bsif")[Guilou001/25-scenario-climatique-bsif]]
  ]
]
#v(1.2em)
#line(length: 100%, stroke: 0.6pt + luma(190))
#v(0.8em)

Une institution financière canadienne doit estimer ce que différents scénarios climatiques feraient à ses emprunteurs. Pour le crédit, le régulateur transforme une probabilité de défaut de départ, puis recalcule la perte attendue. Le présent projet écrit cette règle à partir des formules publiées et vérifie chaque étape contre l'exemple officiel.

Cette reproduction permet ensuite de poser deux questions que l'exemple ne règle pas. Nous cherchons d'abord quelle catégorie d'emprunteurs subit la plus forte hausse relative. Nous tentons également de reconstruire un résultat publié en 2022 pour le secteur du raffinage.

*Résultat principal.* Les huit nombres de l'exemple du BSIF sont retrouvés avec un écart maximal de 1,2 × 10⁻¹⁰ dollar. À vingt ans, la règle augmente la perte attendue de 9,31 % dans la meilleure catégorie de crédit, contre 1,58 % dans la plus faible, soit un effet relatif 5,9 fois plus grand. En effet, la majoration multiplie la cote de défaut plutôt que la probabilité elle-même. Pour le raffinage, la première étape est retrouvée à -71,06 %, contre -72 % publiés, tandis que la suite ne peut pas être reconstruite avec les données publiques.

Afin d'expliquer ces résultats, nous présenterons d'abord le scénario, les probabilités et les pertes utilisées. Dans un deuxième temps, nous déroulerons la formule du BSIF ligne par ligne. Ensuite, nous comparerons les catégories de crédit et nous reprendrons l'exemple du raffinage. Enfin, nous distinguerons ce qui est reproduit de ce qui ne l'est pas, puis nous présenterons les limites et les commandes.

Le rapport détaillé est disponible en PDF : #link("rapport/rapport.pdf")[rapport/rapport.pdf].

== Résumé en anglais

_Summary in English. A from-scratch implementation of the credit module of OSFI's Standardized Climate Scenario Exercise, reproducing every figure of the regulator's own worked example to under a billionth of a dollar, plus two extensions: a sensitivity map showing that a constant logit add-on raises expected credit loss 5.9 times more for the best credit quality bucket than for the worst at twenty years, and a Merton inversion of the 2022 BoC-OSFI pilot's published +450 % default probability._

== 1. La question en détail

Trois questions, dans l'ordre où elles se posent.

*La première est de vérification.* Le BSIF publie une méthode en toutes lettres et un exemple chiffré. Un exercice réglementaire se code-t-il depuis ses formules seules, sans le tableur ? Si oui, tout intermédiaire du dépôt se compare à un nombre publié, et le dépôt cesse d'être une interprétation.

*La deuxième est de fond.* Le régulateur prescrit une majoration de probabilité de défaut par secteur, région et qualité de crédit. Cette majoration s'ajoute au *logit* de la probabilité, le logarithme de sa cote. Quelle exposition en souffre le plus ? La réponse est entièrement contenue dans la forme de la formule.

*La troisième est celle d'un chiffre resté seul.* Le rapport du projet pilote de 2022 annonce que les produits pétroliers raffinés voient leur probabilité de défaut monter de 450 % d'ici 2050. D'où vient ce nombre, et que faut-il supposer d'un emprunteur pour l'obtenir ?

En mots simples : un régulateur demande aux banques de dire combien le climat leur coûterait. Ce dépôt refait le calcul, puis regarde qui la règle frappe et si le chiffre le plus cité tient debout.

== 2. D'où vient le projet, et ce qu'il apporte

L'*exercice normalisé de scénarios climatiques* est le calcul standardisé que le BSIF impose depuis 2024 : chaque institution rend, pour quatre horizons et trois trajectoires de transition, l'écart de sa perte de crédit attendue. Les résultats du premier tour étaient dus le 13 décembre 2024 pour les modules de crédit et de marché. Il fait suite au projet pilote mené en 2021 et 2022 par la Banque du Canada et le BSIF avec six institutions.

Quatre apports.

- *Le module de crédit, écrit depuis les formules publiées* et non depuis le tableur, avec les huit

nombres de l'exemple officiel retrouvés.

- *Un tableau de sensibilité* qui n'existe nulle part : la hausse de perte attendue par \*\*catégorie de

qualité de crédit\*\*, la tranche de probabilité de défaut dans laquelle le BSIF range une exposition, et par échéance. Elle est calculée sur la seule colonne de majorations publiée.

- *La reconstruction du premier maillon du rapport de 2022* depuis le fichier public, et la

déclaration explicite que le second maillon n'est pas reconstructible.

- *Une inversion de Merton* qui répond à une question différente de celle du rapport, et le dit.

Elle fait apparaître un plafond que le rapport ne mentionne pas : exiger que la probabilité de défaut soit multipliée par 5,5 impose qu'elle vaille au moins 18,18 % avant le choc.

Aucun dépôt public ne traite ce sujet. La recherche du 2026-08-30 sur « OSFI standardized climate scenario exercise » et « climate transition scenario credit » ne renvoie que deux dépôts, sans étoile, dont aucun ne lit le fichier canadien.

== 3. Les données, et leur licence

Quatre fichiers publics, téléchargés par script, jamais commités. Tailles mesurées le 2026-08-30.

#table(
  columns: 4,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Fichier*],
    [*Ce qu'il contient*],
    [*Taille*],
    [*Licence*],
    [#raw("scse-instructions-enasc-en_2.xlsx")],
    [22 feuilles, dont cinq exemples travaillés ; c'est celui de crédit qui sert ici],
    [212 911 o],
    [BSIF, usage avec attribution],
    [#raw("scse-workbook-classeur-enasc-en_0.xlsx")],
    [le classeur à remplir, 13 feuilles],
    [1 971 516 o],
    [BSIF, usage avec attribution],
    [#raw("climate-transition-scenario-data.csv")],
    [59 584 observations, 9 géographies, 4 scénarios, 15 secteurs, 66 variables, 2020 à 2050 sans trou],
    [7 026 127 o],
    [Banque du Canada, usage et copie avec attribution],
    [#raw("BoC-OSFI-Using-Scenario-Analysis...pdf")],
    [le rapport du pilote, 62 pages],
    [2 407 957 o],
    [Banque du Canada et BSIF],
)

Deux de ces quatre fichiers sont lus par le code, le classeur d'instructions et le fichier de la Banque du Canada. Le classeur à remplir et le rapport du pilote servent de source documentaire, et aucun module ni aucun test ne les ouvre.

Comment lire ce tableau, en trois constats. Le premier est que la méthode elle-même n'est pas un fichier : elle vit sur une page web du BSIF, formules comprises, et c'est de là que viennent les quatre équations codées ici. Le deuxième est que l'adresse du rapport a dû être corrigée : elle est sous #raw("/uploads/2021/11/") et non sous #raw("/uploads/2022/01/"), chemin qui répond *404* alors que le rapport porte la date de janvier 2022. Le troisième est que le téléchargement passe par le magasin de certificats du système, faute de quoi Python échoue là où #raw("curl") réussit sur la même machine.

== 4. La méthode, pas à pas

+ *Passer à la probabilité conditionnelle.* La probabilité inconditionnelle de défaillir à l'année _i_ est celle de défaillir cette année-là vue d'aujourd'hui ; la conditionnelle est celle de défaillir sachant qu'on a survécu jusque-là. On divise donc par la survie accumulée. Sur l'exemple, 3,5 % en deuxième année sur une survie de 96 % donne 3,645 833 % de conditionnelle.
+ *Ajouter la majoration sur l'échelle logit.* Le *logit* d'une probabilité _p_ est #raw("ln(p / (1 − p))"), le logarithme de sa cote. La majoration prescrite s'y ajoute, ce qui garantit que le résultat reste entre zéro et un.
+ *Revenir à l'inconditionnel* en remultipliant par les survies climatiques.
+ *Ajuster la perte en cas de défaut par la relation de Frye-Jacobs*, qui lie perte et probabilité de défaut par un seul paramètre. Quand la probabilité monte, la perte en cas de défaut monte aussi, parce que les défaillances se concentrent dans les mauvaises années, où les garanties valent moins. Sur l'exemple, 80,00 % devient 80,24 % quand la probabilité passe de 4,00 % à 4,30 %.
+ *Sommer la perte actualisée* année par année, produit de la probabilité, de la perte en cas de défaut et de l'exposition, puis pondérer les trois scénarios macroéconomiques.

== 5. Les résultats

=== 5.1 L'exemple officiel, retrouvé jusqu'au dernier chiffre

L'exposition du cas est de trois millions de dollars sur le secteur du charbon au Canada, six ans de vie restante, taux d'actualisation de 10 %, trois scénarios pondérés 60, 30 et 10 %.

#table(
  columns: 4,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Grandeur*],
    [*Recalculé*],
    [*Publié par le BSIF*],
    [*Écart*],
    [Perte de référence, scénario pessimiste],
    [186 072,387 572],
    [186 072,387 572],
    [0],
    [Perte de référence, scénario de base],
    [131 137,225 870],
    [131 137,225 870],
    [0],
    [Perte de référence, scénario optimiste],
    [113 038,218 836],
    [113 038,218 836],
    [0],
    [Perte de référence, pondérée],
    [162 288,422 188],
    [162 288,422 188],
    [2,9e-11],
    [Perte climatique, horizon 2030],
    [170 170,011 519],
    [170 170,011 519],
    [2,9e-11],
    [Perte climatique, horizon 2035],
    [171 611,306 912],
    [171 611,306 912],
    [-8,7e-11],
    [Perte climatique, horizon 2040],
    [173 324,046 835],
    [173 324,046 835],
    [-1,2e-10],
    [Perte climatique, horizon 2045],
    [175 357,348 595],
    [175 357,348 595],
    [-2,9e-11],
)

Comment lire ce tableau, en trois constats. Le premier est que l'écart le plus grand vaut 1,2e-10 dollar sur 173 324 dollars, soit un écart relatif de 7e-16 : c'est la précision de l'arithmétique flottante, donc l'égalité. Le deuxième est que les six probabilités et les six pertes en cas de défaut de l'horizon 2045 sont retrouvées elles aussi, la première série exactement, la seconde à 1,2e-15. Le troisième est que ces chiffres ne sont pas retapés à la main. La commande #raw("scc verifier") ré-extrait du classeur d'instructions téléchargé les huit lignes de ce tableau, plus les probabilités, les pertes en cas de défaut, les expositions et les 21 majorations qui les produisent. Ses dix contrôles sortent tous « identique ». Ce que le tableau n'établit pas : l'exemple porte sur une seule exposition, et l'accord avec lui ne dit rien des cas que le BSIF ne déroule pas.

#figure(image("../results/figures/exemple_bsif.png", width: 100%), caption: [Les quatre pertes attendues de l'exemple du BSIF, recalculées contre publiées])

Comment lire cette figure : chaque barre part de la perte attendue avant climat, si bien que sa hauteur est la hausse elle-même. Le losange est la valeur publiée par le BSIF, et il se pose au sommet de sa barre à chaque horizon. L'exercice ajoute de 4,86 % à 8,05 % de perte attendue selon l'horizon.

=== 5.2 La majoration frappe les bons emprunteurs, en proportion

C'est le résultat que l'exemple officiel ne montre pas, parce qu'il ne porte que sur un seau de qualité. La majoration s'ajoute au logit, donc multiplie la cote de défaut par l'exponentielle de la majoration. Cette cote vaut presque la probabilité quand celle-ci est petite, et bien plus qu'elle quand elle est grande.

#table(
  columns: 5,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Seau de qualité*],
    [*Probabilité de défaut annuelle*],
    [*Hausse de la perte attendue à 1 an*],
    [*à 5 ans*],
    [*à 20 ans*],
    [1],
    [0,03 %],
    [8,34 %],
    [8,90 %],
    [*9,31 %*],
    [2],
    [0,13 %],
    [8,44 %],
    [8,99 %],
    [9,34 %],
    [3],
    [0,50 %],
    [8,55 %],
    [9,04 %],
    [9,16 %],
    [4],
    [2,65 %],
    [8,68 %],
    [8,75 %],
    [7,65 %],
    [5],
    [11,83 %],
    [8,47 %],
    [6,79 %],
    [3,38 %],
    [6],
    [28,28 %],
    [7,69 %],
    [3,84 %],
    [*1,58 %*],
)

Comment lire ce tableau, en trois constats. Le premier est que le rapport entre le meilleur et le pire seau passe de 1,08 à un an à *5,88 à vingt ans*. La formule ne traite donc pas les qualités de crédit de la même façon, et l'écart se creuse avec l'échéance. Les deux nombres en gras sont les deux termes de ce rapport et non les extrêmes de leur colonne : le maximum à vingt ans est le seau 2, à 9,34 %. Le deuxième constat est le sens de cet écart, contraire à l'intuition : c'est le bon emprunteur dont la perte attendue monte le plus, en proportion. Le troisième est que l'effet de l'échéance change de signe selon le seau, mais pas au même moment pour tous. Les seaux 1 et 2 montent jusqu'à vingt ans, le seau 3 culmine à dix ans, le seau 4 à cinq ans, et les seaux 5 et 6 décroissent dès la première année. Un emprunteur fragile a peu de chances d'être encore là dans quinze ans, et sa perte attendue lointaine pèse donc peu. Ce que le tableau n'établit pas : la majoration employée est celle d'un seul secteur, donc l'écart mesuré est celui de la formule et non celui du risque climatique propre à chaque seau.

#figure(image("../results/figures/carte_sensibilite.png", width: 100%), caption: [La hausse de la perte attendue par seau de qualité et par échéance])

Comment lire cette figure : une ligne par seau de qualité, l'échéance en abscisse. À un an la ligne du haut est le seau 4, et les trois meilleures qualités n'occupent les trois premières places qu'à partir de cinq ans. Les seaux 1 et 2 montent ensuite jusqu'à vingt ans, le seau 3 culmine à dix ans. Le seau 4 décline doucement à partir de cinq ans, et les seaux 5 et 6, les deux plus mauvaises qualités, s'effondrent dès la première année.

#figure(image("../results/figures/mecanique_logit.png", width: 100%), caption: [Pourquoi : la majoration multiplie la cote et non la probabilité])

Comment lire cette figure : en abscisse la probabilité de défaut avant majoration, en échelle logarithmique ; en ordonnée la hausse qu'elle subit, en pourcentage de sa valeur initiale. La ligne tiretée est le plafond #raw("exp(majoration) − 1"), soit 7,90 % pour la majoration de 2046, atteint quand la probabilité tend vers zéro. Les points marquent le milieu de chaque seau.

Ce plafond de 7,90 % est plus bas que les 9,31 % du seau 1 dans le tableau ci-dessus, et deux différences les réconcilient. La figure ne porte que la majoration de 2046, la plus faible des vingt que le tableau emploie ; le chemin complet monte à 0,086 700 en 2050 puis se prolonge, et son plafond vaut 9,06 %. Seconde différence, la figure porte la seule probabilité de défaut quand le tableau porte la perte attendue, perte en cas de défaut comprise. Cette seconde différence ajoute 0,49 point au seau 1 à vingt ans, qui passe de 8,82 % à 9,31 %. Les six lignes du calcul sont dans #raw("results/reconciliation_plafond.csv").

*Ce que cela change en pratique.* Une institution qui lit son résultat d'exercice verra la hausse la plus forte sur la part la mieux notée et la plus longue de son livre. Ce n'est pas un signal sur le risque climatique de ces expositions, c'est une propriété de la fonction logit. Statut : *mesuré* sur la seule colonne de majorations publiée, celle du charbon canadien au seau 4, appliquée à tous les seaux. C'est une hypothèse, déclarée, et c'est exactement ce qu'il faut pour isoler l'effet de la formule.

Une seconde série de quatre hausses vit dans #raw("results/hausse_par_horizon.csv") : celle du même portefeuille stylisé, au seau 4 et sur six ans, aux quatre horizons de l'exercice. Elle vaut 5,28 %, 6,25 %, 7,40 % et 8,72 %, et ne se confond pas avec les 4,86 % à 8,05 % de la section 5.1, qui portent sur l'exposition de l'exemple du BSIF.

=== 5.3 Le rapport de 2022 : un maillon se refait, l'autre pas

#table(
  columns: 4,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Secteur*],
    [*Résultat net 2050 recalculé*],
    [*Publié page 32 du PDF, folio 31*],
    [*Écart*],
    [Produits pétroliers raffinés],
    [*-71,06 %*],
    [-72 %],
    [0,94 point],
    [Cultures],
    [*-30,11 %*],
    [-32 %],
    [1,89 point],
    [Charbon],
    [-84,94 %],
    [non publié],
    [],
    [Pétrole],
    [-79,59 %],
    [non publié],
    [],
    [Gaz],
    [-70,47 %],
    [non publié],
    [],
    [Transport commercial],
    [+8,91 %],
    [non publié],
    [],
)

Le tableau montre six des dix lignes calculables. Les dix sont dans #raw("results/secteurs_resultat_net.csv"), dont « Pétrole et gaz », que la figure plus bas écarte parce qu'il est la somme de « Pétrole » et de « Gaz », au dernier chiffre publié près.

Comment lire ce tableau, en trois constats. Le premier est que le résultat net ne figure pas dans le fichier : il se construit comme les produits moins les coûts directs d'émission moins les coûts indirects. Cette soustraction retrouve les deux valeurs publiées à un et deux points près. Le deuxième est que l'écart résiduel n'est pas expliqué et s'écrit comme tel : il peut venir d'un arrondi de publication, d'une pondération par l'exposition, ou d'une définition du résultat net légèrement différente. Statut : *non expliqué*. Le troisième est que le secteur de l'électricité, cité par le rapport, est absent de ce tableau. Le fichier porte bien ses produits et ses coûts directs d'émission, 136,0 et 0,3 milliards de dollars US de 2014 en référence pour 2050, mais aucun coût indirect. C'est ce seul poste manquant qui l'écarte, et le statut de son résultat net est *non trouvé*, non zéro. Ce que le tableau n'établit pas : deux lignes sur six sont comparées à un chiffre publié, les quatre autres ne sont comparées à rien.

#figure(image("../results/figures/secteurs_2050.png", width: 100%), caption: [Le résultat net par secteur en 2050, recalculé, avec les deux valeurs publiées])

Comment lire cette figure : une barre par secteur, la variation contre le scénario de référence. Neuf barres et non dix, parce que « Pétrole et gaz » est la somme de « Pétrole » et de « Gaz », et que les trois côte à côte compteraient deux fois la même activité. Les deux losanges sont les seules valeurs que le rapport publie, et l'écart est écrit à côté de chacune.

#figure(image("../results/figures/cascade_raffinage.png", width: 100%), caption: [La décomposition du résultat net du raffinage, avant et après])

Comment lire cette figure : deux cascades, la même échelle. Elle montre d'où vient la baisse. Les coûts directs d'émission ne montent que de *0,45 à 1,04 milliard*, et les coûts indirects baissent de *13,14 à 5,21 milliards*. Ce qui s'effondre, ce sont les produits, étiquetés au sommet de la première barre de chaque volet, de 98,4 à 30,8 milliards, soit *-68,7 %*. Le prix du carbone ne ruine pas le raffineur ; la disparition de sa demande le ruine. Les quatre postes sont dans #raw("results/cascade_raffinage.csv").

*Ce qui ne se refait pas.* Le rapport dit page 30 du PDF, folio 29, que la hausse de probabilité de défaut vient d'évaluations d'emprunteurs faites par six institutions sur leurs propres dossiers. Ces évaluations sont complétées par du jugement d'expert, puis résumées par un modèle de type Merton, et elles ne sont pas publiques. Le second maillon est donc *non reconstructible*, et le dépôt l'écrit plutôt que de fabriquer un chiffre qui y ressemblerait.

=== 5.4 Ce qu'il faudrait supposer pour obtenir +450 %

Une question différente se pose au même chiffre, et celle-là se répond. Dans le modèle de *Merton*, qui traite les capitaux propres comme une option d'achat sur les actifs de l'entreprise, quel emprunteur faudrait-il pour qu'une perte de valeur de 71,1 % multiplie sa probabilité de défaut par 5,5 ?

#table(
  columns: 7,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Horizon*],
    [*Volatilité d'actif 15 %*],
    [*20 %*],
    [*25 %*],
    [*30 %*],
    [*40 %*],
    [*50 %*],
    [1 an],
    [*18,18 %*],
    [*18,18 %*],
    [18,18 %],
    [18,17 %],
    [17,92 %],
    [17,04 %],
    [2 ans],
    [18,18 %],
    [18,18 %],
    [18,10 %],
    [17,77 %],
    [16,10 %],
    [13,51 %],
    [3 ans],
    [18,18 %],
    [18,11 %],
    [17,71 %],
    [16,78 %],
    [13,79 %],
    [10,31 %],
    [5 ans],
    [18,13 %],
    [17,59 %],
    [16,21 %],
    [14,22 %],
    [9,76 %],
    [5,93 %],
    [7 ans],
    [17,94 %],
    [16,65 %],
    [14,41 %],
    [11,76 %],
    [6,85 %],
    [3,43 %],
    [10 ans],
    [17,33 %],
    [14,95 %],
    [11,83 %],
    [*8,74 %*],
    [4,04 %],
    [1,54 %],
)

Comment lire ce tableau, en trois constats. Chaque case est la probabilité de défaut que l'emprunteur devrait avoir *avant* le choc, cumulée jusqu'à l'horizon de sa ligne et non annuelle. Les 17,33 % de la case à dix ans et 15 % de volatilité valent 1,89 % par an. Le premier constat est que dans la plage de volatilité d'actif ordinaire d'une entreprise cotée, de 15 % à 30 %, la réponse tient entre *8,74 % et 18,18 %*. Il faut donc un emprunteur qui défaille déjà entre une fois sur cinq et demi et une fois sur onze et demi, de qualité spéculative, et non un emprunteur de première catégorie. Le deuxième est que le haut du tableau ne bouge plus. Dès que le choc suffit à rendre le défaut presque certain, le rapport de 5,5 ne peut être atteint que si la probabilité de départ vaut *1 / 5,5 = 18,18 %*. Ce plafond est un fait d'arithmétique et non un résultat du modèle. Le troisième est que ce calcul n'est pas celui de la Banque du Canada : c'est une question posée à son chiffre, sous une hypothèse déclarée, celle que la valeur d'actif suit le résultat net. Statut : *modélisé*.

Ce plafond se démontre en une ligne. Une probabilité ne peut pas dépasser un, donc le rapport de la probabilité d'après à celle d'avant ne peut pas dépasser l'inverse de celle d'avant. Exiger un rapport de 5,5 impose donc une probabilité de départ d'au moins un sur cinq et demi, soit 18,18 %. Le module le retrouve à la sixième décimale : à un an et 15 % de volatilité, il rend une probabilité de départ de 18,182 % pour une probabilité d'arrivée de 1,000000.

#figure(image("../results/figures/inversion_merton.png", width: 100%), caption: [Le levier et la probabilité de défaut de départ qu'il faudrait])

Comment lire cette figure : le levier requis à gauche, la probabilité de défaut de départ à droite, et la bande grisée est la plage usuelle de volatilité d'actif. Les deux courbes sont tracées à l'horizon de cinq ans seulement, une seule ligne du tableau ci-dessus. La courbe de droite s'aplatit à gauche parce qu'elle bute sur le plafond de 18,18 %, et non parce que le modèle s'y stabilise. Son titre arrondit la borne haute de la bande, 18,1 % à cinq ans, à une fois sur cinq et demi.

== 6. Reproduire

#raw("uv sync --locked --all-extras\nuv run pytest                 # 37 tests, dont 36 fermés et sans réseau, moins d'une seconde\nuv run scc fetch              # les quatre fichiers publics, environ 11 Mo\nuv run scc verifier           # les constantes du dépôt contre le classeur d'instructions du BSIF\nuv run scc tout               # les quatre calculs et les six figures", block: true, lang: "bash")

Le résultat publié auquel nous comparons le calcul vit dans #raw("src/scc/exemple.py"), et #raw("scc verifier") est la commande qui prouve que cette vérité est bien celle du régulateur. Un seul test lit #raw("data/raw"), celui qui rattache la baisse de valeur de 71,1 % du modèle de Merton à sa mesure ; il est sauté quand le fichier manque. Les chiffres de ce README viennent des fichiers de #raw("results/"), sauf ceux que voici. Les chiffres de la section 3 et les deux valeurs de l'électricité de la section 5.3 se lisent dans #raw("data/raw/"). Ceux de la section 4 et les vingt et une majorations sont les constantes de #raw("src/scc/exemple.py"), confrontées au classeur d'instructions du BSIF par #raw("scc verifier"). Ses dix contrôles en sortent « identique », donc à écart nul. L'écart de 1,2e-15 sur les pertes en cas de défaut de 2045 est d'une autre nature : c'est celui de la série recalculée contre ces constantes, et il se mesure dans #raw("tests/test_scse.py"). Les dix contrôles se comptent dans #raw("src/scc/cli.py"), et les 37 tests dans la sortie de #raw("pytest"). Les quatre chiffres de sensibilité au plancher, au tableau des limites, s'obtiennent en faisant varier la constante #raw("PLANCHER") de #raw("src/scc/sensibilite.py").

== 7. Limites, avec leur statut

#table(
  columns: 2,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Limite*],
    [*Statut*],
    [Les majorations réelles de probabilité de défaut ne sont fournies qu'aux institutions déclarantes ; l'exemple n'en publie qu'une colonne, charbon, Canada, seau 4],
    [déclaré ; tout ce dépôt calcule sur cette colonne et sur un portefeuille stylisé, jamais sur une société nommée],
    [Le tableau de sensibilité applique la majoration de la catégorie 4 à toutes les catégories],
    [hypothèse déclarée ; c'est ce qui isole l'effet de la formule, et non une lecture du BSIF],
    [L'écart de 0,94 et 1,89 point sur les deux valeurs publiées du rapport de 2022],
    [non expliqué ; arrondi de publication, pondération par l'exposition ou définition du résultat net sont les trois pistes, aucune n'est vérifiée],
    [Le second maillon du rapport de 2022, du résultat net à la probabilité de défaut],
    [non reconstructible ; les évaluations d'emprunteurs des six institutions ne sont pas publiques],
    [L'inversion de Merton suppose que la valeur d'actif suit proportionnellement le résultat net],
    [hypothèse déclarée ; elle répond à une autre question que celle du rapport, et le dépôt ne prétend pas le contraire],
    [Le secteur de l'électricité n'a aucun coût indirect dans le fichier public, alors qu'il en a les produits et les coûts directs d'émission],
    [non trouvé ; son résultat net ne se calcule pas, et il est absent du tableau plutôt que compté zéro],
    [La première catégorie part de zéro, dont le milieu géométrique n'existe pas : le tableau de sensibilité lui impose un plancher de 1 point de base, d'où sa probabilité de 0,03 %],
    [hypothèse déclarée ; mesuré en faisant varier ce plancher de 1e-3 à 1e-6, la hausse de la catégorie 1 à vingt ans va de 9,342 % à 9,221 % et le rapport entre extrêmes de 5,902 à 5,825, contre 5,882 publié],
    [« Pétrole et gaz » est la somme de « Pétrole » et de « Gaz » dans le fichier de la Banque du Canada, au dernier chiffre publié près],
    [mesuré ; la ligne reste dans #raw("results/secteurs_resultat_net.csv") avec sa marque #raw("agregat"), et la figure des secteurs l'écarte],
    [Seuls les modules de crédit sont codés, pas ceux de marché, d'immobilier, d'inondation ni de feux de forêt],
    [déclaré ; les quatre autres exemples travaillés du classeur restent ouverts],
    [Le portefeuille stylisé prend un hasard de défaut constant, une perte en cas de défaut de 45 % et un taux de 5 %],
    [hypothèses déclarées ; elles ne mettent aucune structure par terme dans le résultat],
)

== 8. Crédits, licence, citation

Données du Bureau du surintendant des institutions financières et de la Banque du Canada, employées avec attribution et jamais redistribuées. Relation entre probabilité et perte en cas de défaut de Jon Frye et Michael Jacobs (2012), telle que la méthode du BSIF la prescrit. Code sous licence MIT, rapport sous licence CC BY 4.0. Figures produites par #link("https://github.com/Guilou001/gv-fintools")[gv-fintools], la couche partagée du portefeuille.

Le rapport #raw("rapport/rapport.pdf") est engendré depuis ce README, une seule source et deux formes.

Voisinage dans le portefeuille : #link("https://github.com/Guilou001/10-credit-bancaire")[10-credit-bancaire] porte le modèle de probabilité de défaut et la perte attendue IFRS 9 hors climat, et #link("https://github.com/Guilou001/17-alm-assurance-vie")[17-alm-assurance-vie] porte le module de taux du test de suffisance du capital des assureurs vie. Ce dépôt-ci ne refait ni l'un ni l'autre : il code une mécanique réglementaire et mesure ce qu'elle fait.
