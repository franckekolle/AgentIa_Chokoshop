"""
Validate a WooCommerce product CSV before import.

Examples:
    python scripts/validate_catalogue.py --csv data/produits_avec_descriptions.csv
    python scripts/validate_catalogue.py --csv data/produits_avec_descriptions.csv --images-root produits/images --check-media
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from importer_woocommerce import (
    DESCRIPTION_BLOCKS_TO_REMOVE,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    clean_product_description,
    fix_text_encoding,
    parse_price,
    parse_stock,
)


REQUIRED_COLUMNS = {"reference", "nom", "categorie", "prix", "description", "dossier_images"}
MOJIBAKE_HINTS = ("Ã", "Â", "â€", "â€™", "â€œ", "â€�", "â€“", "â€”")


def read_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not csv_path.exists():
        raise ValueError(f"CSV introuvable: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [fix_text_encoding(name) for name in (reader.fieldnames or [])]
        rows = [
            {
                fix_text_encoding(key): fix_text_encoding(value or "").strip()
                for key, value in row.items()
            }
            for row in reader
        ]

    if not fieldnames:
        raise ValueError("Le CSV ne contient pas d'en-tete.")
    if not rows:
        raise ValueError("Le CSV ne contient aucun produit.")

    return fieldnames, rows


def has_media(folder: Path) -> bool:
    if not folder.exists() or not folder.is_dir():
        return False

    media_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    return any(path.is_file() and path.suffix.lower() in media_extensions for path in folder.iterdir())


def validate_catalog(csv_path: Path, images_root: Path, check_media: bool) -> list[str]:
    errors: list[str] = []
    fieldnames, rows = read_rows(csv_path)

    missing_columns = REQUIRED_COLUMNS - set(fieldnames)
    if missing_columns:
        errors.append(f"Colonnes manquantes: {', '.join(sorted(missing_columns))}")
        return errors

    references_seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        reference = row.get("reference", "").strip()
        label = reference or f"ligne {index}"

        if not reference:
            errors.append(f"Ligne {index}: reference vide.")
        elif reference in references_seen:
            errors.append(f"{label}: reference en doublon.")
        references_seen.add(reference)

        for column in ["nom", "categorie", "prix", "dossier_images"]:
            if not row.get(column, "").strip():
                errors.append(f"{label}: colonne {column} vide.")

        try:
            parse_price(row.get("prix", ""))
        except Exception as exc:
            errors.append(f"{label}: prix invalide ({exc}).")

        try:
            parse_stock(row.get("stock", "1"))
        except Exception as exc:
            errors.append(f"{label}: stock invalide ({exc}).")

        for column, value in row.items():
            if any(hint in value for hint in MOJIBAKE_HINTS):
                errors.append(f"{label}: encodage suspect dans {column}.")
                break

        description = row.get("description", "")
        if clean_product_description(description) != description:
            errors.append(f"{label}: description contient un bloc interdit ou des espaces a nettoyer.")
        elif any(block in description for block in DESCRIPTION_BLOCKS_TO_REMOVE):
            errors.append(f"{label}: description contient un bloc interdit.")

        if check_media:
            folder = images_root / row.get("dossier_images", "")
            if not has_media(folder):
                errors.append(f"{label}: aucun media trouve dans {folder}.")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valider un catalogue produits WooCommerce.")
    parser.add_argument("--csv", type=Path, default=Path("data/produits_avec_descriptions.csv"))
    parser.add_argument("--images-root", type=Path, default=Path("produits/images"))
    parser.add_argument("--check-media", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        errors = validate_catalog(args.csv, args.images_root, args.check_media)
    except Exception as exc:
        print(f"Validation impossible: {exc}", file=sys.stderr)
        return 1

    if errors:
        print(f"Validation echouee: {len(errors)} probleme(s).", file=sys.stderr)
        for error in errors[:100]:
            print(f"- {error}", file=sys.stderr)
        if len(errors) > 100:
            print(f"- ... {len(errors) - 100} probleme(s) supplementaire(s)", file=sys.stderr)
        return 1

    print(f"Validation OK: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
