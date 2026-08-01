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
    classer_medias_ai.py        # Classement d'un dossier média mélangé

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

Publier directement les produits sur le site avec images :

```bash
python scripts/importer_woocommerce.py --csv data/produits_avec_descriptions.csv --images-root produits/images --execute --publish
```

Publier directement en mettant a jour les produits existants :

```bash
python scripts/importer_woocommerce.py --csv data/produits_avec_descriptions.csv --images-root produits/images --execute --update-existing --keep-existing-images --publish
```

## CI/CD GitHub

Le workflow GitHub Actions est dans `.github/workflows/ci-cd.yml`.

Il lance automatiquement les controles sur `push` et `pull_request` :

```bash
python -m compileall scripts
python scripts/validate_catalogue.py --csv data/produits_avec_descriptions.csv --images-root produits/images
python scripts/importer_woocommerce.py --csv data/produits_avec_descriptions.csv --images-root produits/images --dry-run --skip-images --skip-videos
```

Pour publier depuis GitHub, va dans `Actions > WooCommerce CI/CD > Run workflow`, puis choisis :

- `validate-only` : controle uniquement.
- `publish-new` : cree et publie les nouveaux produits.
- `publish-update` : met a jour et publie les produits existants.

Ajoute ces secrets dans `Settings > Secrets and variables > Actions` :

```text
WORDPRESS_URL
WOOCOMMERCE_CONSUMER_KEY
WOOCOMMERCE_CONSUMER_SECRET
WORDPRESS_USER
WORDPRESS_APP_PASSWORD
```

Note : `data/` et `produits/` sont ignores par Git car ils contiennent le catalogue et les medias locaux. La CI automatique verifie donc toujours le code, et ne valide le catalogue que si le CSV est disponible dans le run GitHub. Pour publier depuis GitHub Actions, il faudra fournir le catalogue et les medias via un mecanisme dedie, ou lancer la publication depuis ton PC.

Créer ou mettre à jour avec images et vidéos dans la description :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images --execute --update-existing
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

Générer les descriptions et proposer les prix avec IA + recherche web, dans un fichier séparé :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions --use-ai-pricing --web-search --output data/produits_avec_prix_ia.csv
```

Classer un dossier mélangé de photos/vidéos avant import :

```bash
python scripts/classer_medias_ai.py --source chemin/vers/dossier_depart
```

## Documentation

Le manuel complet d'utilisation se trouve ici :

```text
manuel_utilisation_chokoshop.md
```

Il décrit la préparation des dossiers, le remplissage du CSV, les options d'images, les options IA et la procédure de vérification dans WordPress.

