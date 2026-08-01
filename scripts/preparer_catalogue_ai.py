"""
Prepare a WooCommerce product CSV before import.

This script can:
- resize and pad product photos to a square WooCommerce-friendly format;
- read raw descriptions from a text file;
- optionally use OpenAI vision to generate clean product descriptions;
- optionally allow OpenAI web search for product context.

Safe local test without AI:
    python scripts/preparer_catalogue_ai.py

With AI descriptions:
    python scripts/preparer_catalogue_ai.py --use-ai-descriptions

With AI + web search:
    python scripts/preparer_catalogue_ai.py --use-ai-descriptions --web-search

With AI descriptions + pricing:
    python scripts/preparer_catalogue_ai.py --use-ai-descriptions --use-ai-pricing --web-search
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import os
import re
import shutil
from pathlib import Path
from typing import Any


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

DESCRIPTION_BLOCKS_TO_REMOVE = (
    """DÉTAILS VISIBLES
• Type : sac à main femme
• Présentation : anses et corps du sac visibles sur le média associé
• Usage : quotidien, ville ou occasion
• Style : élégant et polyvalent

La marque, le modèle commercial exact, la matière, les dimensions et les accessoires inclus ne sont pas indiqués dans cette fiche tant qu’ils n’ont pas été confirmés avec certitude sur le média original.""",
    "La matière, la taille, le type de pierre ou de finition et la marque ne sont pas affirmés sans vérification certaine.",
    "La marque, la fragrance, la contenance, la texture et les conseils d’application exacts doivent être confirmés sur l’étiquette avant publication.",
    "La marque, la fragrance, la contenance et les conseils d’utilisation exacts doivent être confirmés directement sur l’étiquette avant publication.",
)


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


def clean_product_description(value: str) -> str:
    text = fix_text_encoding(value)
    for block in DESCRIPTION_BLOCKS_TO_REMOVE:
        text = text.replace(block, "")

    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        cleaned_lines.append(line)
        previous_blank = is_blank

    return "\n".join(cleaned_lines).strip()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise SystemExit(f"CSV introuvable : {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [clean_row_text({key: value or "" for key, value in row.items()}) for row in reader]
        fieldnames = [fix_text_encoding(name) for name in list(reader.fieldnames or [])]

    if not rows:
        raise SystemExit(f"Le CSV est vide : {path}")
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    known_fields = list(fieldnames)
    for row in rows:
        for key in row:
            if key not in known_fields:
                known_fields.append(key)
    cleaned_rows = [clean_row_text(row) for row in rows]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=known_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned_rows)


def read_raw_descriptions(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    descriptions: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or " - " not in line:
            continue
        reference, description = line.split(" - ", 1)
        descriptions[fix_text_encoding(reference).strip()] = fix_text_encoding(description).strip()
    return descriptions


def find_images(images_root: Path, folder_name: str) -> list[Path]:
    folder = images_root / folder_name
    if not folder.exists():
        return []

    return sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda path: path.name.lower(),
    )


def find_videos(images_root: Path, folder_name: str) -> list[Path]:
    folder = images_root / folder_name
    if not folder.exists():
        return []

    return sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        ],
        key=lambda path: path.name.lower(),
    )


def copy_videos(video_paths: list[Path], output_folder: Path) -> list[Path]:
    output_folder.mkdir(parents=True, exist_ok=True)
    copied_paths: list[Path] = []
    for index, video_path in enumerate(video_paths, start=1):
        output_path = output_folder / f"video_{index:02d}{video_path.suffix.lower()}"
        shutil.copy2(video_path, output_path)
        copied_paths.append(output_path)
    return copied_paths


def optimize_images(
    image_paths: list[Path],
    output_folder: Path,
    size: int,
    quality: int,
) -> list[Path]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise SystemExit(
            "La librairie Pillow est necessaire pour reformater les images. "
            "Installe-la avec : python -m pip install -r requirements.txt"
        ) from exc

    output_folder.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []

    for index, image_path in enumerate(image_paths, start=1):
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((size, size), Image.Resampling.LANCZOS)

            canvas = Image.new("RGB", (size, size), "white")
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGBA", image.size, "white")
                background.alpha_composite(image.convert("RGBA"))
                image = background.convert("RGB")
            else:
                image = image.convert("RGB")

            left = (size - image.width) // 2
            top = (size - image.height) // 2
            canvas.paste(image, (left, top))

            output_path = output_folder / f"{index:02d}.jpg"
            canvas.save(output_path, "JPEG", quality=quality, optimize=True)
            output_paths.append(output_path)

    return output_paths


def image_to_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    return json.loads(text)


def generate_description_with_ai(
    row: dict[str, str],
    raw_notes: str,
    main_image: Path | None,
    use_web_search: bool,
) -> dict[str, str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "La librairie openai est necessaire pour utiliser l'IA. "
            "Installe-la avec : python -m pip install -r requirements.txt"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY est manquant dans .env")

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5")

    known_data = {
        "reference": row.get("reference", ""),
        "nom_actuel": row.get("nom", ""),
        "categorie": row.get("categorie", ""),
        "prix": row.get("prix", ""),
        "etat": row.get("etat", ""),
        "couleur": row.get("couleur", ""),
        "taille": row.get("taille", ""),
        "marque": row.get("marque", ""),
        "notes_brutes": raw_notes,
    }

    prompt = f"""
Tu aides a preparer une fiche produit WooCommerce pour une boutique de chaussures et vetements.

Donnees connues:
{json.dumps(known_data, ensure_ascii=False, indent=2)}

Consignes:
- Reponds uniquement en JSON valide.
- Ne mens pas sur la marque, le modele, la matiere ou l'etat.
- Si la photo ne permet pas de confirmer une information, reste prudent.
- Si la recherche web est disponible, utilise-la seulement pour enrichir le contexte general du modele ou de la marque, pas pour inventer l'etat exact de cet article.
- Le style doit etre commercial, clair, simple et en francais.
- Evite les promesses non verifiees.

Schema attendu:
{{
  "nom": "titre produit court",
  "description_courte": "1 phrase courte",
  "description": "description complete de 3 a 5 phrases",
  "mots_cles": "liste courte de mots cles separes par des virgules"
}}
""".strip()

    content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
    if main_image is not None:
        content.append(
            {
                "type": "input_image",
                "image_url": image_to_data_url(main_image),
                "detail": "low",
            }
        )

    request: dict[str, Any] = {
        "model": model,
        "input": [{"role": "user", "content": content}],
        "store": False,
    }

    if use_web_search:
        web_tool_type = os.getenv("OPENAI_WEB_TOOL_TYPE", "web_search_preview")
        request["tools"] = [{"type": web_tool_type, "search_context_size": "low"}]

    try:
        response = client.responses.create(**request)
    except Exception as exc:
        if use_web_search:
            raise RuntimeError(
                "La generation IA avec recherche web a echoue. "
                "Essaie d'abord sans --web-search. Si le probleme continue, "
                "verifie OPENAI_WEB_TOOL_TYPE dans .env."
            ) from exc
        raise
    result = parse_json_object(response.output_text)

    return {
        "nom": fix_text_encoding(str(result.get("nom", row.get("nom", "")))).strip(),
        "description_courte": fix_text_encoding(str(result.get("description_courte", ""))).strip(),
        "description": fix_text_encoding(str(result.get("description", ""))).strip(),
        "mots_cles": fix_text_encoding(str(result.get("mots_cles", ""))).strip(),
    }


def normalize_price(value: str) -> str:
    text = fix_text_encoding(value).strip().replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return ""
    amount = float(match.group(0))
    return f"{amount:.2f}"


def generate_price_with_ai(
    row: dict[str, str],
    raw_notes: str,
    main_image: Path | None,
    use_web_search: bool,
) -> dict[str, str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "La librairie openai est necessaire pour utiliser l'IA. "
            "Installe-la avec : python -m pip install -r requirements-ai.txt"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY est manquant dans .env")
    if not use_web_search:
        raise SystemExit("--use-ai-pricing necessite --web-search pour estimer un prix de marche.")

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5")
    known_data = {
        "reference": row.get("reference", ""),
        "nom": row.get("nom", ""),
        "categorie": row.get("categorie", ""),
        "sous_categorie": row.get("sous_categorie", ""),
        "etat": row.get("etat", ""),
        "couleur": row.get("couleur", ""),
        "taille": row.get("taille", ""),
        "pointure": row.get("pointure", ""),
        "marque": row.get("marque", ""),
        "matiere": row.get("matiere", ""),
        "genre": row.get("genre", ""),
        "description": row.get("description", ""),
        "notes_brutes": raw_notes,
    }

    prompt = f"""
Tu aides a proposer un prix de vente prudent pour une boutique WooCommerce de chaussures, vetements, sacs et accessoires.

Donnees du produit:
{json.dumps(known_data, ensure_ascii=False, indent=2)}

Consignes strictes:
- Reponds uniquement en JSON valide.
- Utilise la recherche web pour estimer une fourchette de marche comparable.
- Ne mens pas sur la marque, le modele, la matiere, l'etat, la taille ou la pointure.
- Si les informations sont insuffisantes, reste prudent et mets "prix_a_verifier": "oui".
- Le prix doit etre un prix de vente conseille pour ce produit d'occasion ou a verifier, en euros.
- Ne propose pas un prix neuf si le produit semble d'occasion ou si l'etat n'est pas confirme.
- Si la photo ou le texte ne permettent pas une estimation fiable, donne une fourchette large.

Schema attendu:
{{
  "prix": "prix conseille avec point decimal, exemple 24.90",
  "prix_min_marche": "prix minimum constate/estime",
  "prix_max_marche": "prix maximum constate/estime",
  "prix_a_verifier": "oui|non",
  "prix_source_logique": "explication courte, sans URL obligatoire"
}}
""".strip()

    content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
    if main_image is not None:
        content.append(
            {
                "type": "input_image",
                "image_url": image_to_data_url(main_image),
                "detail": "low",
            }
        )

    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": content}],
        tools=[
            {
                "type": os.getenv("OPENAI_WEB_TOOL_TYPE", "web_search_preview"),
                "search_context_size": "low",
            }
        ],
        store=False,
    )
    result = parse_json_object(response.output_text)

    return {
        "prix": normalize_price(str(result.get("prix", row.get("prix", "")))),
        "prix_min_marche": normalize_price(str(result.get("prix_min_marche", ""))),
        "prix_max_marche": normalize_price(str(result.get("prix_max_marche", ""))),
        "prix_a_verifier": fix_text_encoding(str(result.get("prix_a_verifier", "oui"))).strip() or "oui",
        "prix_source_logique": fix_text_encoding(str(result.get("prix_source_logique", ""))).strip(),
    }


def prepare_catalog(args: argparse.Namespace) -> int:
    load_dotenv(args.env)
    fieldnames, rows = read_csv(args.csv)
    raw_descriptions = read_raw_descriptions(args.descriptions)

    for extra_field in ["description_courte", "mots_cles", "prix_min_marche", "prix_max_marche", "prix_a_verifier", "prix_source_logique"]:
        if extra_field not in fieldnames:
            fieldnames.append(extra_field)

    output_rows: list[dict[str, str]] = []

    for index, row in enumerate(rows, start=1):
        reference = row.get("reference", f"ligne-{index}")
        source_folder = row.get("dossier_images", reference) or reference
        source_images = find_images(args.images_root, source_folder)
        source_videos = find_videos(args.images_root, source_folder)
        optimized_folder = args.optimized_root / reference

        print(f"[{index}/{len(rows)}] {reference} - {row.get('nom', '')}")
        if args.skip_image_formatting:
            optimized_images = source_images
            print("  reformattage images : ignore")
        else:
            optimized_images = optimize_images(source_images, optimized_folder, args.image_size, args.quality)
            copied_videos = copy_videos(source_videos, optimized_folder)
            print(f"  images optimisees : {len(optimized_images)}")
            print(f"  videos copiees : {len(copied_videos)}")

        if not args.skip_image_formatting:
            row["dossier_images"] = reference
        raw_notes = raw_descriptions.get(reference, "")

        if args.use_ai_descriptions:
            ai_data = generate_description_with_ai(
                row=row,
                raw_notes=raw_notes,
                main_image=optimized_images[0] if optimized_images else None,
                use_web_search=args.web_search,
            )
            row["nom"] = ai_data["nom"] or row.get("nom", "")
            row["description_courte"] = ai_data["description_courte"] or row.get("description_courte", "")
            row["description"] = ai_data["description"] or row.get("description", "")
            row["mots_cles"] = ai_data["mots_cles"]
            print("  description IA generee")
        elif raw_notes and not row.get("description"):
            row["description"] = raw_notes

        row["description"] = clean_product_description(row.get("description", ""))

        if args.use_ai_pricing and not row.get("prix", "").strip():
            price_data = generate_price_with_ai(
                row=row,
                raw_notes=raw_notes,
                main_image=optimized_images[0] if optimized_images else None,
                use_web_search=args.web_search,
            )
            row["prix"] = price_data["prix"] or row.get("prix", "")
            row["prix_min_marche"] = price_data["prix_min_marche"]
            row["prix_max_marche"] = price_data["prix_max_marche"]
            row["prix_a_verifier"] = price_data["prix_a_verifier"]
            row["prix_source_logique"] = price_data["prix_source_logique"]
            print("  prix IA propose")
        elif args.use_ai_pricing:
            row.setdefault("prix_a_verifier", "non")

        output_rows.append(row)
        write_csv(args.output, fieldnames, output_rows)

    write_csv(args.output, fieldnames, output_rows)
    print("")
    print(f"Catalogue prepare : {args.output}")
    if not args.skip_image_formatting:
        print(f"Images optimisees : {args.optimized_root}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preparer un CSV produits avec images optimisees et descriptions IA.")
    parser.add_argument("--csv", type=Path, default=Path("data/exemple_produits_chaussures.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/produits_prepares.csv"))
    parser.add_argument("--descriptions", type=Path, default=Path("data/descriptions_brutes_exemple.txt"))
    parser.add_argument("--images-root", type=Path, default=Path("produits/images"))
    parser.add_argument("--optimized-root", type=Path, default=Path("produits/images_optimisees"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--image-size", type=int, default=1200)
    parser.add_argument("--quality", type=int, default=88)
    parser.add_argument(
        "--use-ai-descriptions",
        action="store_true",
        help="Active la generation IA des noms/descriptions. Par defaut, aucune IA n'est utilisee.",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Alias conserve pour compatibilite : active la generation IA des descriptions.",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Option explicite pour rappeler qu'aucune IA ne doit etre utilisee.",
    )
    parser.add_argument("--web-search", action="store_true")
    parser.add_argument(
        "--use-ai-pricing",
        action="store_true",
        help="Propose un prix de marche avec l'IA. Necessite --web-search. Ne remplace pas les prix deja renseignes.",
    )
    parser.add_argument(
        "--skip-image-formatting",
        action="store_true",
        help="Ne reformate pas les images. Le CSV de sortie garde les dossiers images originaux.",
    )
    args = parser.parse_args()

    if args.use_ai:
        args.use_ai_descriptions = True

    if args.use_ai_descriptions and args.no_ai:
        raise SystemExit("Choisis soit --use-ai, soit --no-ai.")
    if args.web_search and not (args.use_ai_descriptions or args.use_ai_pricing):
        raise SystemExit("--web-search necessite --use-ai-descriptions ou --use-ai-pricing.")
    if args.use_ai_pricing and not args.web_search:
        raise SystemExit("--use-ai-pricing necessite --web-search.")
    return args


if __name__ == "__main__":
    raise SystemExit(prepare_catalog(parse_args()))

