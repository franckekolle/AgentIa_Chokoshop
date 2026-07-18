# Agent d'import WooCommerce ChokoShop

Ce projet contient un outil Python pour préparer et publier automatiquement des produits sur un site WordPress/WooCommerce.

Il permet de :

- lire un catalogue produits depuis un fichier CSV ;
- associer chaque produit à son dossier d'images ;
- créer les produits dans WooCommerce en brouillon ou en publication directe ;
- envoyer les images locales vers la médiathèque WordPress ;
- reformater les images au format carré adapté à une boutique en ligne ;
- générer optionnellement des descriptions produits avec l'IA ;
- éviter la création de doublons grâce aux références/SKU.

Par défaut, l'outil fonctionne sans IA et crée les produits en brouillon.

## Structure du projet

```text
Multi_Cluster_gst/
  .env                         # Configuration privée, non versionnée
  .env.example                 # Exemple de configuration
  requirements.txt             # Dépendance minimale WooCommerce
  requirements-ai.txt          # Dépendances optionnelles image/IA

  data/
    exemple_produits_chaussures.csv
    modele_catalogue_general.csv
    produits_prepares.csv

  produits/
    images/                    # Images originales par référence produit
    images_optimisees/          # Images reformattées

  scripts/
    importer_woocommerce.py     # Import des produits dans WooCommerce
    preparer_catalogue_ai.py    # Préparation images et descriptions IA

  manuel_utilisation_chokoshop.md
  woocommerce_automation_guide.md
```

## Configuration

Créer un fichier `.env` à partir de `.env.example`, puis renseigner :

```text
WORDPRESS_URL=https://chokoshop.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxxxxxxxxxxxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxxxxxxxxxxxxxx
WORDPRESS_USER=identifiant_ou_email_wordpress
WORDPRESS_APP_PASSWORD=mot_de_passe_application_wordpress
```

Pour utiliser l'IA, ajouter aussi :

```text
OPENAI_API_KEY=sk_xxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-5
```

Le fichier `.env` contient des secrets et ne doit pas être partagé.

## Installation

Installation minimale :

```bash
python -m pip install -r requirements.txt
```

Installation optionnelle pour le reformattage d'images et l'IA :

```bash
python -m pip install -r requirements-ai.txt
```

## Utilisation principale

Tester sans créer de produit :

```bash
python scripts/importer_woocommerce.py --dry-run
```

Créer les produits en brouillon sans images :

```bash
python scripts/importer_woocommerce.py --execute --skip-images
```

Créer les produits en brouillon avec images :

```bash
python scripts/importer_woocommerce.py --execute
```

Mettre à jour les produits existants :

```bash
python scripts/importer_woocommerce.py --execute --update-existing
```

Préparer les images avant import :

```bash
python scripts/preparer_catalogue_ai.py
```

Importer le catalogue préparé :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

Mettre à jour les produits existants avec le catalogue préparé :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute --update-existing
```

Relancer automatiquement les uploads en cas d'erreur serveur temporaire :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute --update-existing --upload-retries 8 --retry-delay 10
```

Générer les descriptions avec l'IA :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions
```

Générer les descriptions avec IA et recherche web :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions --web-search
```

## Documentation

Le manuel complet d'utilisation se trouve ici :

```text
manuel_utilisation_chokoshop.md
```

Il décrit la préparation des dossiers, le remplissage du CSV, les options d'images, les options IA et la procédure de vérification dans WordPress.
