# Procedure pour automatiser l'ajout de produits WooCommerce

Ce guide explique comment preparer tes photos, tes descriptions et tes prix pour publier automatiquement des produits sur un site WordPress avec WooCommerce.

L'objectif recommande est de commencer avec un import semi-automatique : le script cree les produits en brouillon, tu verifies dans WordPress, puis tu publies.

## 1. Preparer WordPress et WooCommerce

### 1.1 Verifier WooCommerce

Dans ton tableau de bord WordPress :

1. Va dans `Extensions`.
2. Verifie que `WooCommerce` est installe et active.
3. Va dans `Produits`.
4. Verifie que tu peux creer un produit manuellement.

### 1.2 Creer les categories

Dans WordPress :

1. Va dans `Produits > Categories`.
2. Cree les categories principales :
   - Chaussures
   - Vetements
   - Pantalons
   - Robes
   - Accessoires

Tu pourras ajouter d'autres categories plus tard.

### 1.3 Creer les cles API WooCommerce

Dans WordPress :

1. Va dans `WooCommerce > Reglages`.
2. Ouvre l'onglet `Avance`.
3. Clique sur `API REST`.
4. Clique sur `Ajouter une cle`.
5. Mets une description, par exemple `Import automatique produits`.
6. Choisis ton utilisateur administrateur.
7. Mets les permissions sur `Lecture/Ecriture`.
8. Clique sur `Generer une cle API`.

WooCommerce va afficher :

- `Consumer key`
- `Consumer secret`

Garde ces deux valeurs. Elles serviront au script Python.

Important : ne partage jamais ces cles publiquement.

## 2. Organiser les photos des produits

Il n'est pas obligatoire de mettre les images dans une base de donnees au debut.

La methode la plus simple consiste a utiliser un dossier par produit :

```text
produits/
  images/
    CH001/
      01.jpg
      02.jpg
      03.jpg
    CH002/
      01.jpg
      02.jpg
    CH003/
      01.jpg
```

Chaque dossier doit utiliser une reference produit claire :

- `CH001` pour une chaussure
- `PA001` pour un pantalon
- `VE001` pour un vetement

Cette reference sera aussi presente dans le fichier CSV.

## 3. Preparer le fichier des produits

Le fichier principal peut etre un CSV ou un Excel. Pour commencer, le CSV est le plus simple.

Colonnes recommandees :

```text
reference,nom,categorie,prix,stock,etat,couleur,taille,marque,description_courte,description,dossier_images,statut
```

Explication des colonnes :

- `reference` : identifiant unique du produit, par exemple `CH001`.
- `nom` : titre visible sur le site.
- `categorie` : categorie WooCommerce.
- `prix` : prix de vente.
- `stock` : quantite disponible.
- `etat` : neuf, tres bon etat, bon etat, occasion.
- `couleur` : couleur principale.
- `taille` : pointure ou taille.
- `marque` : marque du produit.
- `description_courte` : texte court visible pres du prix.
- `description` : description complete du produit.
- `dossier_images` : dossier contenant les photos.
- `statut` : `draft` au debut, puis `publish` quand tu seras pret.

## 4. Workflow conseille

### Etape A - Preparation locale

1. Rassembler toutes les photos dans `produits/images/`.
2. Creer un dossier par article.
3. Creer ou remplir le fichier `data/exemple_produits_chaussures.csv`.
4. Verifier que chaque `reference` correspond a un dossier image.

### Etape B - Generation/amélioration IA

L'agent IA peut ensuite :

1. Lire le nom, l'etat, la marque, la taille et les notes.
2. Produire une description propre.
3. Corriger les fautes.
4. Uniformiser le style.
5. Eventuellement proposer des mots-cles SEO.

Exemple :

```text
Notes brutes :
Basket Nike noire, pointure 42, tres bon etat, portee peu, semelle propre.

Description generee :
Basket Nike noire pour homme, pointure 42, en tres bon etat. Modele confortable et polyvalent, adapte a une utilisation quotidienne. Semelle propre, usure tres legere visible sur les photos.
```

### Etape C - Publication WooCommerce

Le script Python devra :

1. Lire le CSV.
2. Envoyer les images dans WordPress.
3. Creer le produit WooCommerce.
4. Associer les images au produit.
5. Mettre le produit en brouillon.
6. Enregistrer les erreurs dans un fichier de suivi.

### Etape D - Verification

Dans WordPress :

1. Va dans `Produits`.
2. Filtre les produits en `Brouillon`.
3. Ouvre chaque fiche.
4. Verifie le prix, les images, la categorie et la description.
5. Publie seulement les produits valides.

## 5. Informations necessaires pour creer le script

Pour automatiser vraiment la publication, il faudra renseigner :

```text
WORDPRESS_URL=https://ton-site.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxxxxxxxxxxxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxxxxxxxxxxxxxx
```

Ces informations seront placees dans un fichier `.env`, qui ne doit pas etre partage.

## 6. Faut-il une base de donnees ?

Pas au debut.

Pour commencer :

- un dossier d'images suffit ;
- un fichier CSV ou Excel suffit ;
- un script Python suffit.

Une base SQLite pourra etre ajoutee plus tard si tu veux suivre :

- les produits deja importes ;
- les produits en erreur ;
- les produits modifies ;
- la date de publication ;
- les liens WordPress des fiches creees.

## 7. Regle de securite recommandee

Au debut, utilise toujours :

```text
statut=draft
```

Cela evite de publier automatiquement une fiche avec une mauvaise photo, un mauvais prix ou une description incomplete.

## 8. Lancer le script Python

Le script d'import est disponible ici :

```text
scripts/importer_woocommerce.py
```

### 8.1 Installer la dependance Python minimale

Dans le terminal VS Code :

```bash
python -m pip install -r requirements.txt
```

### 8.2 Creer le fichier `.env`

Copie le fichier `.env.example` vers `.env`, puis remplace les valeurs :

```text
WORDPRESS_URL=https://ton-site.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxxxxxxxxxxxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxxxxxxxxxxxxxx
WORDPRESS_USER=ton_identifiant_wordpress
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

Les variables `WORDPRESS_USER` et `WORDPRESS_APP_PASSWORD` servent a envoyer les images locales dans la bibliotheque WordPress.

### 8.3 Tester sans rien creer

```bash
python scripts/importer_woocommerce.py --dry-run
```

Ce mode lit le CSV, verifie les dossiers images et affiche ce qui serait envoye.

### 8.4 Creer les produits en brouillon

```bash
python scripts/importer_woocommerce.py --execute
```

Par securite, le script force le statut `draft`.

### 8.5 Creer les produits sans images

Si tu veux tester la creation des fiches sans envoyer les photos :

```bash
python scripts/importer_woocommerce.py --execute --skip-images
```

## 9. Preparer les descriptions et les photos

Avant l'import WooCommerce, tu peux preparer un catalogue enrichi avec :

```text
scripts/preparer_catalogue_ai.py
```

Ce script sert a :

- reformater les photos en carre `1200 x 1200` ;
- convertir les images en JPEG optimise ;
- conserver le produit au centre sur fond blanc ;
- lire les notes brutes dans `data/descriptions_brutes_exemple.txt` ;
- generer une description propre avec l'IA seulement si tu l'actives ;
- optionnellement autoriser une recherche web seulement si tu l'actives.

Par defaut, l'IA n'est pas utilisee.

### 9.1 Installer les dependances optionnelles

Si tu veux reformater les images ou utiliser l'IA :

```bash
python -m pip install -r requirements-ai.txt
```

### 9.2 Preparer seulement les images, sans IA

```bash
python scripts/preparer_catalogue_ai.py
```

Sorties creees :

```text
data/produits_prepares.csv
produits/images_optimisees/
```

### 9.3 Ne pas reformater les images

Si tu veux garder les images originales :

```bash
python scripts/preparer_catalogue_ai.py --skip-image-formatting
```

### 9.4 Generer les descriptions avec l'IA

Ajoute dans `.env` :

```text
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-5
```

Puis lance :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions
```

### 9.5 Autoriser la recherche web

Si tu veux que l'IA cherche des informations generales sur le modele ou la marque :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions --web-search
```

Attention : la recherche web peut aider pour le contexte general, mais elle ne doit pas inventer l'etat exact de ton article. L'etat reel doit venir de tes photos et de tes notes.

### 9.6 Importer le catalogue prepare dans WooCommerce

Apres preparation :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```
