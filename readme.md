# README — Projet de Clustering Hiérarchique pour Données Géostatistiques Multivariées

## Description du projet

Ce projet implémente une méthode de **clustering hiérarchique** appliquée aux **données géostatistiques multivariées**, inspirée de l’article scientifique :

> *A Hierarchical Clustering Method for Multivariate Geostatistical Data* de Francky Fouedjio

L’objectif principal est de regrouper des zones géographiques ou des observations spatiales présentant des caractéristiques statistiques similaires, tout en prenant en compte les dépendances spatiales entre les données.

---

## Objectifs

* Analyser des données géostatistiques multivariées.
* Appliquer des techniques de classification hiérarchique.
* Intégrer la composante spatiale dans le processus de clustering.
* Visualiser les groupes obtenus sur des données spatiales.

---

## Méthodologie

Le projet repose sur :

1. **Prétraitement des données**

   * Nettoyage
   * Normalisation
   * Gestion des coordonnées spatiales

2. **Analyse géostatistique**

   * Étude des corrélations spatiales
   * Construction des matrices de distance / dissimilarité

3. **Clustering hiérarchique**

   * Algorithmes agglomératifs
   * Mesures de similarité adaptées aux données multivariées
   * Génération du dendrogramme

4. **Visualisation**

   * Représentation des clusters
   * Cartographie spatiale des résultats

---

## Packages utilisées

* Python
* NumPy
* Pandas
* SciPy
* Scikit-learn
* Matplotlib / Seaborn
* GeoPandas

---

## Structure du projet

```bash
project/
│
├── data/               # Données d'entrée
├── notebooks/          # Analyses exploratoires
├── src/                # Code source principal
├── results/            # Résultats et figures
├── README.md
└── requirements.txt
```

---

## Résultats attendus

* Identification de structures spatiales cohérentes
* Segmentation géographique des données
* Visualisation claire des clusters hiérarchiques

---

## Référence scientifique

Francky Fouedjio,
A hierarchical clustering method for multivariate geostatistical data,
Spatial Statistics,
Volume 18, Part B,
2016,
Pages 333-351,

---
