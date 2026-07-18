"""
Import products from a CSV file into WooCommerce as drafts.

The script:
- reads product rows from a CSV file;
- uploads local images to the WordPress media library;
- creates WooCommerce simple products;
- keeps products in draft by default.

Before running it for real, test with:
    python scripts/importer_woocommerce.py --dry-run

Then run the import:
    python scripts/importer_woocommerce.py --execute
"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â€™", "â€œ", "â€�", "â€“", "â€”")
MOJIBAKE_REPLACEMENTS = {
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€�": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¦": "...",
    "Â ": " ",
    "Â": "",
}


def fix_text_encoding(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    text = value
    if any(marker in text for marker in MOJIBAKE_MARKERS):
        try:
            text = text.encode("cp1252").decode("utf-8")
        except UnicodeError:
            pass

    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)

    return text


def clean_row_text(row: dict[str, str]) -> dict[str, str]:
    return {fix_text_encoding(key): fix_text_encoding(value).strip() for key, value in row.items()}


@dataclass
class Config:
    wordpress_url: str
    wc_key: str
    wc_secret: str
    wp_user: str | None
    wp_app_password: str | None

    @property
    def wc_api_base(self) -> str:
        return urljoin(self.wordpress_url.rstrip("/") + "/", "wp-json/wc/v3/")

    @property
    def wp_api_base(self) -> str:
        return urljoin(self.wordpress_url.rstrip("/") + "/", "wp-json/wp/v2/")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env(name: str, allow_missing: bool = False) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        if allow_missing:
            return ""
        raise SystemExit(f"Variable manquante dans .env : {name}")
    return value


def load_config(env_path: Path, allow_missing: bool = False) -> Config:
    load_dotenv(env_path)
    return Config(
        wordpress_url=require_env("WORDPRESS_URL", allow_missing) or "https://ton-site.com",
        wc_key=require_env("WOOCOMMERCE_CONSUMER_KEY", allow_missing),
        wc_secret=require_env("WOOCOMMERCE_CONSUMER_SECRET", allow_missing),
        wp_user=os.getenv("WORDPRESS_USER", "").strip() or None,
        wp_app_password=os.getenv("WORDPRESS_APP_PASSWORD", "").strip() or None,
    )


def read_products(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise SystemExit(f"CSV introuvable : {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [clean_row_text({key: value or "" for key, value in row.items()}) for row in reader]

    if not rows:
        raise SystemExit(f"Le CSV est vide : {csv_path}")

    required = {"reference", "nom", "categorie", "prix", "description", "dossier_images"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"Colonnes manquantes dans le CSV : {', '.join(sorted(missing))}")

    return rows


def find_images(images_root: Path, folder_name: str) -> list[Path]:
    folder = images_root / folder_name
    if not folder.exists():
        return []

    images = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda path: path.name.lower())


def find_videos(images_root: Path, folder_name: str) -> list[Path]:
    folder = images_root / folder_name
    if not folder.exists():
        return []

    videos = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(videos, key=lambda path: path.name.lower())


def request_json(response: requests.Response, context: str) -> Any:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text

    if not response.ok:
        pretty = json.dumps(payload, ensure_ascii=False, indent=2) if isinstance(payload, dict) else payload
        raise RuntimeError(f"{context} a echoue [{response.status_code}] : {pretty}")

    return payload


def request_with_retries(
    method: str,
    url: str,
    context: str,
    retries: int,
    retry_delay: float,
    **kwargs: Any,
) -> requests.Response:
    retry_statuses = {429, 500, 502, 503, 504}
    last_response: requests.Response | None = None

    for attempt in range(1, retries + 2):
        response = requests.request(method, url, **kwargs)
        if response.status_code not in retry_statuses:
            return response

        last_response = response
        if attempt <= retries:
            wait_seconds = retry_delay * attempt
            print(
                f"  {context} temporairement indisponible "
                f"[{response.status_code}], nouvel essai dans {wait_seconds:.0f}s..."
            )
            time.sleep(wait_seconds)

    return last_response


def wc_get(config: Config, endpoint: str, params: dict[str, Any] | None = None) -> Any:
    response = request_with_retries(
        "GET",
        urljoin(config.wc_api_base, endpoint),
        f"GET WooCommerce {endpoint}",
        retries=2,
        retry_delay=2,
        auth=HTTPBasicAuth(config.wc_key, config.wc_secret),
        params=params,
        timeout=60,
    )
    return request_json(response, f"GET WooCommerce {endpoint}")


def wc_post(config: Config, endpoint: str, payload: dict[str, Any]) -> Any:
    response = request_with_retries(
        "POST",
        urljoin(config.wc_api_base, endpoint),
        f"POST WooCommerce {endpoint}",
        retries=2,
        retry_delay=2,
        auth=HTTPBasicAuth(config.wc_key, config.wc_secret),
        json=payload,
        timeout=60,
    )
    return request_json(response, f"POST WooCommerce {endpoint}")


def wc_put(config: Config, endpoint: str, payload: dict[str, Any]) -> Any:
    response = request_with_retries(
        "PUT",
        urljoin(config.wc_api_base, endpoint),
        f"PUT WooCommerce {endpoint}",
        retries=2,
        retry_delay=2,
        auth=HTTPBasicAuth(config.wc_key, config.wc_secret),
        json=payload,
        timeout=60,
    )
    return request_json(response, f"PUT WooCommerce {endpoint}")


def find_product_by_sku(config: Config, sku: str) -> dict[str, Any] | None:
    found = wc_get(config, "products", {"sku": sku, "per_page": 1})
    if found:
        return found[0]
    return None


def ensure_category(config: Config, category_name: str, cache: dict[str, int]) -> int:
    normalized = category_name.strip().lower()
    if normalized in cache:
        return cache[normalized]

    found = wc_get(config, "products/categories", {"search": category_name, "per_page": 100})
    for category in found:
        if category.get("name", "").strip().lower() == normalized:
            cache[normalized] = int(category["id"])
            return cache[normalized]

    created = wc_post(config, "products/categories", {"name": category_name})
    cache[normalized] = int(created["id"])
    return cache[normalized]


def upload_media(
    config: Config,
    image_path: Path,
    alt_text: str,
    retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    if not config.wp_user or not config.wp_app_password:
        raise RuntimeError(
            "Images locales detectees, mais WORDPRESS_USER ou WORDPRESS_APP_PASSWORD est manquant."
        )

    mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    headers = {
        "Content-Disposition": f'attachment; filename="{image_path.name}"',
        "Content-Type": mime_type,
    }

    response = request_with_retries(
        "POST",
        urljoin(config.wp_api_base, "media"),
        f"Upload image {image_path.name}",
        retries=retries,
        retry_delay=retry_delay,
        auth=HTTPBasicAuth(config.wp_user, config.wp_app_password),
        headers=headers,
        data=image_path.read_bytes(),
        timeout=120,
    )

    media = request_json(response, f"Upload image {image_path.name}")

    if alt_text:
        requests.post(
            urljoin(config.wp_api_base, f"media/{media['id']}"),
            auth=HTTPBasicAuth(config.wp_user, config.wp_app_password),
            json={"alt_text": alt_text, "title": alt_text},
            timeout=60,
        )

    return media


def parse_price(value: str) -> str:
    price = value.replace(",", ".").strip()
    if not price:
        raise ValueError("prix vide")
    float(price)
    return price


def parse_stock(value: str) -> int:
    if not value:
        return 1
    return int(float(value.replace(",", ".")))


def build_product_payload(
    row: dict[str, str],
    category_id: int,
    image_ids: list[int],
    video_urls: list[str],
    publish: bool,
) -> dict[str, Any]:
    reference = row["reference"]
    status = row.get("statut", "draft") or "draft"
    if publish:
        status = "publish"
    else:
        status = "draft"

    description = fix_text_encoding(row.get("description", ""))
    if video_urls:
        video_html = build_video_description_html(video_urls)
        description = f"{description}\n\n{video_html}" if description else video_html

    payload: dict[str, Any] = {
        "name": fix_text_encoding(row["nom"]),
        "type": "simple",
        "status": status,
        "sku": reference,
        "regular_price": parse_price(row["prix"]),
        "description": description,
        "short_description": fix_text_encoding(row.get("description_courte", "")),
        "categories": [{"id": category_id}],
        "manage_stock": True,
        "stock_quantity": parse_stock(row.get("stock", "1")),
        "images": [{"id": image_id} for image_id in image_ids],
    }

    attributes = []
    for name, key in [
        ("Etat", "etat"),
        ("Couleur", "couleur"),
        ("Taille", "taille"),
        ("Marque", "marque"),
    ]:
        value = row.get(key, "")
        if value:
            attributes.append({"name": name, "visible": True, "options": [fix_text_encoding(value)]})

    if attributes:
        payload["attributes"] = attributes

    return payload


def build_video_description_html(video_urls: list[str]) -> str:
    blocks = ["<h3>Video du produit</h3>"]
    for url in video_urls:
        escaped_url = (
            url.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        blocks.append(
            '<video controls preload="metadata" style="width:100%;max-width:720px;height:auto;">'
            f'<source src="{escaped_url}">'
            "Votre navigateur ne peut pas lire cette video."
            "</video>"
        )
    return "\n".join(blocks)


def import_products(args: argparse.Namespace) -> int:
    config = load_config(args.env, allow_missing=not args.execute)
    products = read_products(args.csv)
    category_cache: dict[str, int] = {}
    created_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0

    print(f"CSV : {args.csv}")
    print(f"Images : {args.images_root}")
    print(f"Site : {config.wordpress_url}")
    print(f"Mode : {'execution reelle' if args.execute else 'dry-run'}")
    print("")

    for index, row in enumerate(products, start=1):
        reference = row.get("reference", f"ligne-{index}")
        try:
            images = [] if args.skip_images else find_images(args.images_root, row["dossier_images"])
            videos = [] if args.skip_videos else find_videos(args.images_root, row["dossier_images"])
            print(f"[{index}/{len(products)}] {reference} - {row['nom']}")

            if args.execute:
                existing = find_product_by_sku(config, reference)
                if existing and not args.update_existing:
                    skipped_count += 1
                    print(
                        f"  deja existant : #{existing['id']} "
                        f"({existing.get('status', 'statut inconnu')}) - ignore"
                    )
                    continue

                category_id = ensure_category(config, row["categorie"], category_cache)
                payload = build_product_payload(row, category_id, [], [], args.publish)
                media_ids = []
                video_urls = []

                if existing and args.update_existing and args.keep_existing_images:
                    media_ids = [int(image["id"]) for image in existing.get("images", []) if image.get("id")]
                    print(f"  images conservees : {len(media_ids)}")
                else:
                    for image_path in images:
                        media = upload_media(
                            config,
                            image_path,
                            row["nom"],
                            retries=args.upload_retries,
                            retry_delay=args.retry_delay,
                        )
                        media_ids.append(int(media["id"]))
                        print(f"  image envoyee : {image_path.name} -> media #{media['id']}")

                for video_path in videos:
                    media = upload_media(
                        config,
                        video_path,
                        row["nom"],
                        retries=args.upload_retries,
                        retry_delay=args.retry_delay,
                    )
                    video_url = media.get("source_url")
                    if video_url:
                        video_urls.append(str(video_url))
                    print(f"  video envoyee : {video_path.name} -> media #{media['id']}")

                payload["images"] = [{"id": image_id} for image_id in media_ids]
                if video_urls:
                    description = fix_text_encoding(row.get("description", ""))
                    video_html = build_video_description_html(video_urls)
                    payload["description"] = f"{description}\n\n{video_html}" if description else video_html

                if existing and args.update_existing:
                    payload.pop("sku", None)
                    updated = wc_put(config, f"products/{existing['id']}", payload)
                    print(f"  produit mis a jour : #{updated['id']} ({updated.get('status', 'draft')})")
                    updated_count += 1
                else:
                    created = wc_post(config, "products", payload)
                    print(f"  produit cree : #{created['id']} ({created.get('status', 'draft')})")
                    created_count += 1
            else:
                print(f"  categorie : {row['categorie']}")
                print(f"  prix : {row['prix']}")
                print(f"  images trouvees : {len(images)}")
                print(f"  videos trouvees : {len(videos)}")
                print("  aucune creation : dry-run")

        except Exception as exc:
            failed_count += 1
            print(f"  ERREUR {reference} : {exc}", file=sys.stderr)

    print("")
    print(
        f"Termine. Produits crees : {created_count}. "
        f"Mis a jour : {updated_count}. Ignorés : {skipped_count}. Erreurs : {failed_count}."
    )
    return 1 if failed_count else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importer des produits WooCommerce depuis un CSV.")
    parser.add_argument("--csv", type=Path, default=Path("data/exemple_produits_chaussures.csv"))
    parser.add_argument("--images-root", type=Path, default=Path("produits/images"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--execute", action="store_true", help="Cree vraiment les produits.")
    parser.add_argument("--dry-run", action="store_true", help="Teste sans creer de produit.")
    parser.add_argument("--skip-images", action="store_true", help="Cree les produits sans envoyer les images.")
    parser.add_argument("--skip-videos", action="store_true", help="Ignore les videos presentes dans les dossiers produits.")
    parser.add_argument("--publish", action="store_true", help="Publie directement les produits. Par defaut: draft.")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Met a jour les produits existants trouves par reference/SKU.",
    )
    parser.add_argument(
        "--keep-existing-images",
        action="store_true",
        help="Avec --update-existing, conserve les images deja presentes dans WooCommerce.",
    )
    parser.add_argument(
        "--upload-retries",
        type=int,
        default=5,
        help="Nombre de nouveaux essais pour les uploads images en erreur temporaire.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=5,
        help="Delai de base en secondes entre deux essais. Le delai augmente a chaque essai.",
    )
    args = parser.parse_args()

    if args.execute and args.dry_run:
        raise SystemExit("Choisis soit --execute, soit --dry-run, pas les deux.")
    if args.keep_existing_images and not args.update_existing:
        raise SystemExit("--keep-existing-images necessite --update-existing.")

    return args


if __name__ == "__main__":
    raise SystemExit(import_products(parse_args()))
