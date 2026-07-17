# Manuel d'utilisation - Agent d'import WooCommerce ChokoShop

Ce manuel explique comment utiliser l'outil d'import automatique des produits dans WooCommerce.

L'outil permet de :

- preparer les produits dans un fichier CSV ;
- organiser les photos par article ;
- reformater les images si l'utilisateur le souhaite ;
- generer les descriptions avec l'IA si l'utilisateur le souhaite ;
- creer les produits dans WooCommerce en brouillon ou les publier directement.

Par defaut, l'outil n'utilise pas l'IA et cree les produits en brouillon.

## 1. Dossier de travail

Tous les fichiers doivent rester dans ce dossier :

```text
C:\Users\ekolleessoh\Multi_Cluster_gst
```

Structure recommandee :

```text
Multi_Cluster_gst/
  .env
  requirements.txt
  requirements-ai.txt

  data/
    exemple_produits_chaussures.csv
    produits_prepares.csv
    descriptions_brutes_exemple.txt

  produits/
    images/
      CH001/
        01.jpg
        02.jpg
        03.jpg
      CH002/
        01.jpg
        02.jpg
        03.jpg

    images_optimisees/

  scripts/
    importer_woocommerce.py
    preparer_catalogue_ai.py
```

## 2. Fichier `.env`

Le fichier `.env` contient les acces au site WordPress/WooCommerce.

Il doit etre place ici :

```text
C:\Users\ekolleessoh\Multi_Cluster_gst\.env
```

Exemple :

```text
WORDPRESS_URL=https://chokoshop.com
WOOCOMMERCE_CONSUMER_KEY=ck_xxxxxxxxxxxxxxxxx
WOOCOMMERCE_CONSUMER_SECRET=cs_xxxxxxxxxxxxxxxxx

WORDPRESS_USER=identifiant_ou_email_wordpress
WORDPRESS_APP_PASSWORD=mot de passe application wordpress

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5
OPENAI_WEB_TOOL_TYPE=web_search_preview
```

Roles des champs :

- `WORDPRESS_URL` : adresse du site, sans `/wp-admin`.
- `WOOCOMMERCE_CONSUMER_KEY` : cle API WooCommerce commencant par `ck_`.
- `WOOCOMMERCE_CONSUMER_SECRET` : cle secrete WooCommerce commencant par `cs_`.
- `WORDPRESS_USER` : identifiant ou email de connexion WordPress.
- `WORDPRESS_APP_PASSWORD` : mot de passe d'application WordPress, necessaire pour envoyer les images.
- `OPENAI_API_KEY` : optionnel, seulement pour generer les descriptions avec l'IA.

Ne jamais partager le contenu du fichier `.env`.

## 3. Installation Python

Installation minimale pour creer les produits WooCommerce :

```bash
python -m pip install -r requirements.txt
```

Installation optionnelle pour reformater les images et utiliser l'IA :

```bash
python -m pip install -r requirements-ai.txt
```

## 4. Organisation des images

Chaque article doit avoir son propre dossier d'images.

Exemple :

```text
produits/images/CH001/01.jpg
produits/images/CH001/02.jpg
produits/images/CH001/03.jpg

produits/images/CH002/01.jpg
produits/images/CH002/02.jpg
produits/images/CH002/03.jpg
```

La reference du dossier doit correspondre a la colonne `dossier_images` du CSV.

Exemple CSV :

```csv
reference,dossier_images
CH001,CH001
CH002,CH002
```

Formats images acceptes :

```text
.jpg
.jpeg
.png
.webp
```

## 5. Fichier CSV des produits

Le fichier CSV principal se place dans :

```text
data/
```

Exemple :

```text
data/exemple_produits_chaussures.csv
```

Colonnes minimales obligatoires :

```text
reference,nom,categorie,prix,stock,description,dossier_images,statut
```

Colonnes recommandees :

```text
reference,nom,categorie,sous_categorie,prix,stock,etat,couleur,taille,pointure,marque,matiere,genre,description_courte,description,dossier_images,statut
```

Signification :

- `reference` : code unique de l'article, par exemple `CH001`.
- `nom` : nom du produit affiche sur WooCommerce.
- `categorie` : categorie principale, par exemple `Chaussures`, `Vetements`, `Sacs`.
- `sous_categorie` : type plus precis, par exemple `Baskets`, `Robe`, `Sac a main`.
- `prix` : prix de vente, par exemple `49.99`.
- `stock` : quantite disponible.
- `etat` : `Neuf`, `Tres bon etat`, `Bon etat`, `Occasion`.
- `couleur` : couleur principale.
- `taille` : taille textile, par exemple `S`, `M`, `L`, `XL`, `38`, `40`.
- `pointure` : pointure chaussure, par exemple `39`, `42`, `43`.
- `marque` : marque si connue.
- `matiere` : cuir, coton, jean, polyester, similicuir, etc.
- `genre` : homme, femme, enfant, mixte.
- `description_courte` : phrase courte de presentation.
- `description` : description complete.
- `dossier_images` : nom du dossier photo dans `produits/images/`.
- `statut` : `draft` recommande au debut.

## 6. Champs conseilles selon le type d'article

### Chaussures

Champs importants :

```text
reference,nom,categorie,prix,stock,etat,couleur,pointure,marque,matiere,genre,description,dossier_images,statut
```

Exemple :

```csv
CH001,Baskets Running Air Max,Chaussures,89.90,1,Tres bon etat,Noir,42,Nike,Tissu et caoutchouc,Homme,"Baskets confortables pour usage quotidien.",CH001,draft
```

### Vetements

Champs importants :

```text
reference,nom,categorie,prix,stock,etat,couleur,taille,marque,matiere,genre,description,dossier_images,statut
```

Exemple :

```csv
VE001,Veste jean femme,Vetements,34.90,1,Bon etat,Bleu,M,Zara,Jean,Femme,"Veste en jean bleue, coupe classique.",VE001,draft
```

### Pantalons

Champs importants :

```text
reference,nom,categorie,prix,stock,etat,couleur,taille,marque,matiere,genre,description,dossier_images,statut
```

Exemple :

```csv
PA001,Pantalon chino homme,Pantalons,29.90,1,Tres bon etat,Beige,42,Generic,Coton,Homme,"Pantalon chino beige en tres bon etat.",PA001,draft
```

### Sacs de femme

Champs importants :

```text
reference,nom,categorie,prix,stock,etat,couleur,marque,matiere,genre,description,dossier_images,statut
```

Exemple :

```csv
SA001,Sac a main noir,Sacs,44.90,1,Tres bon etat,Noir,Generic,Similicuir,Femme,"Sac a main noir elegant avec rangement interieur.",SA001,draft
```

### Accessoires

Champs importants :

```text
reference,nom,categorie,prix,stock,etat,couleur,marque,matiere,genre,description,dossier_images,statut
```

Exemple :

```csv
AC001,Ceinture cuir marron,Accessoires,14.90,1,Bon etat,Marron,Generic,Cuir,Homme,"Ceinture marron classique en bon etat.",AC001,draft
```

## 7. Descriptions brutes

Les descriptions brutes sont optionnelles.

Fichier :

```text
data/descriptions_brutes_exemple.txt
```

Format attendu :

```text
CH001 - Basket noire, pointure 42, tres bon etat, semelle propre.
VE001 - Veste jean femme taille M, bon etat, couleur bleue.
SA001 - Sac noir femme, tres bon etat, rangement interieur.
```

Ces notes peuvent etre utilisees par l'IA pour generer des descriptions propres.

## 8. Utilisation sans IA

Cette option est recommandee pour le premier usage.

Elle utilise seulement les informations deja presentes dans le CSV.

Tester sans creer de produit :

```bash
python scripts/importer_woocommerce.py --dry-run
```

Creer les produits en brouillon sans images :

```bash
python scripts/importer_woocommerce.py --execute --skip-images
```

Creer les produits en brouillon avec images :

```bash
python scripts/importer_woocommerce.py --execute
```

Publier directement les produits :

```bash
python scripts/importer_woocommerce.py --execute --publish
```

Recommandation : utiliser d'abord les brouillons, puis publier depuis WordPress apres verification.

## 9. Reformater les images

Le reformattage des images est optionnel.

Commande :

```bash
python scripts/preparer_catalogue_ai.py
```

Cette commande :

- lit le CSV dans `data/exemple_produits_chaussures.csv` ;
- lit les images dans `produits/images/` ;
- cree des images carrees en `1200 x 1200` ;
- place les images optimisees dans `produits/images_optimisees/` ;
- cree le CSV prepare `data/produits_prepares.csv`.

Importer ensuite les produits avec les images optimisees :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

Ne pas reformater les images :

```bash
python scripts/preparer_catalogue_ai.py --skip-image-formatting
```

## 10. Generation IA des descriptions

La generation IA est optionnelle.

Elle ne s'active jamais automatiquement.

Pour l'utiliser, renseigner dans `.env` :

```text
OPENAI_API_KEY=sk_xxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-5
```

Generer les descriptions avec l'IA :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions
```

Generer les descriptions avec IA et recherche web :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions --web-search
```

La recherche web sert seulement a enrichir le contexte general du produit.

L'IA utilise :

- les champs du CSV ;
- les notes brutes si elles existent ;
- la premiere image du produit si elle existe ;
- la recherche web seulement si l'option `--web-search` est ajoutee.

Le CSV final est cree ici :

```text
data/produits_prepares.csv
```

Importer ensuite :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

## 11. Choix du niveau d'automatisation

### Mode manuel controle

Utiliser le CSV deja rempli :

```bash
python scripts/importer_woocommerce.py --execute
```

### Mode preparation images seulement

```bash
python scripts/preparer_catalogue_ai.py
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

### Mode IA pour descriptions

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

### Mode IA avec recherche web

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions --web-search
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

## 12. Verification dans WordPress

Apres import :

1. Aller dans `WordPress > Produits > Tous les produits`.
2. Filtrer les produits en `Brouillon`.
3. Ouvrir chaque produit.
4. Verifier :
   - nom ;
   - prix ;
   - stock ;
   - categorie ;
   - description ;
   - images ;
   - taille ou pointure ;
   - etat de l'article.
5. Cliquer sur `Publier` si tout est correct.

## 13. Commandes principales

Test sans creation :

```bash
python scripts/importer_woocommerce.py --dry-run
```

Creation en brouillon sans images :

```bash
python scripts/importer_woocommerce.py --execute --skip-images
```

Creation en brouillon avec images :

```bash
python scripts/importer_woocommerce.py --execute
```

Preparation des images :

```bash
python scripts/preparer_catalogue_ai.py
```

Preparation IA des descriptions :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions
```

Preparation IA avec recherche web :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions --web-search
```

Import du catalogue prepare :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

Publication directe :

```bash
python scripts/importer_woocommerce.py --execute --publish
```

## 14. Erreurs courantes

`OPENAI_API_KEY est manquant dans .env`

Cause : l'option IA est activee, mais aucune cle OpenAI n'est renseignee.

Solution : ajouter `OPENAI_API_KEY` dans `.env` ou relancer sans `--use-ai-descriptions`.

`insufficient_quota`

Cause : le compte OpenAI API n'a pas de credit disponible.

Solution : utiliser le mode sans IA ou ajouter du credit API OpenAI.

`Images locales detectees, mais WORDPRESS_USER ou WORDPRESS_APP_PASSWORD est manquant`

Cause : le script essaie d'envoyer les images, mais les acces WordPress media ne sont pas renseignes.

Solution : renseigner `WORDPRESS_USER` et `WORDPRESS_APP_PASSWORD` dans `.env`.

`deja existant - ignore`

Cause : un produit avec la meme reference existe deja dans WooCommerce.

Solution : verifier le produit existant dans WordPress. Le script evite les doublons.

## 15. Workflow recommande

Pour un nouvel arrivage de produits :

1. Creer les dossiers images dans `produits/images/`.
2. Remplir le CSV dans `data/`.
3. Tester :

```bash
python scripts/importer_woocommerce.py --dry-run
```

4. Preparer les images si besoin :

```bash
python scripts/preparer_catalogue_ai.py
```

5. Generer les descriptions IA seulement si souhaite :

```bash
python scripts/preparer_catalogue_ai.py --use-ai-descriptions
```

6. Importer en brouillon :

```bash
python scripts/importer_woocommerce.py --csv data/produits_prepares.csv --images-root produits/images_optimisees --execute
```

7. Verifier dans WordPress.
8. Publier les produits valides.

