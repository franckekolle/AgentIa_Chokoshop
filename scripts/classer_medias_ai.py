"""
Class mixed product photos/videos into WooCommerce-ready product folders.

The script never modifies the source folder. It creates:
- a review CSV describing the proposed grouping;
- a WooCommerce-ready product CSV;
- optionally, copied media folders under produits/images/ when --execute is used.

Dry run:
    python scripts/classer_medias_ai.py --source chemin/vers/dossier_melange

Copy files after review:
    python scripts/classer_medias_ai.py --source chemin/vers/dossier_melange --execute
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v", ".vlc"}
CSV_FIELDS = [
    "reference",
    "nom",
    "categorie",
    "sous_categorie",
    "prix",
    "stock",
    "etat",
    "couleur",
    "taille",
    "pointure",
    "marque",
    "matiere",
    "genre",
    "description_courte",
    "description",
    "dossier_images",
    "statut",
]
REVIEW_FIELDS = [
    "reference",
    "fichier_source",
    "type_media",
    "fichier_destination",
    "groupe_ia",
    "confiance",
    "raison",
]


@dataclass
class MediaFile:
    path: Path
    kind: str
    label: str
    number: int | None
    mtime: float


@dataclass
class ProductGroup:
    group_id: str
    reference: str
    media: list[MediaFile]
    name: str
    category: str
    sub_category: str
    color: str
    gender: str
    brand: str
    material: str
    short_description: str
    description: str
    confidence: str
    reason: str


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def natural_key(path: Path) -> list[Any]:
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def extract_number(path: Path) -> int | None:
    matches = re.findall(r"\d+", path.stem)
    if not matches:
        return None
    return int(matches[-1])


def discover_media(source: Path) -> list[MediaFile]:
    if not source.exists():
        raise SystemExit(f"Dossier source introuvable : {source}")

    files: list[MediaFile] = []
    for path in sorted(source.rglob("*"), key=natural_key):
        if not path.is_file():
            continue
        if not path.exists():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            kind = "image"
        elif suffix in VIDEO_EXTENSIONS:
            kind = "video"
        else:
            continue

        files.append(
            MediaFile(
                path=path,
                kind=kind,
                label=f"F{len(files) + 1:04d}",
                number=extract_number(path),
                mtime=path.stat().st_mtime,
            )
        )

    if not files:
        raise SystemExit(f"Aucun media compatible trouve dans : {source}")
    return files


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_source_folder(args: argparse.Namespace) -> None:
    source = args.source.resolve()
    project_root = Path.cwd().resolve()
    target_root = args.target_root.resolve()
    work_dir = args.work_dir.resolve()

    if source == project_root:
        raise SystemExit(
            "Le dossier source ne doit pas etre la racine du projet. "
            "Cree plutot un dossier separe, par exemple : produits/a_classer"
        )
    if source == target_root or is_relative_to(source, target_root):
        raise SystemExit(
            "Le dossier source ne doit pas etre dans produits/images. "
            "Utilise un dossier brut separe, par exemple : produits/a_classer"
        )
    if is_relative_to(target_root, source):
        raise SystemExit(
            "Le dossier source ne doit pas contenir produits/images. "
            "Utilise un dossier brut separe, par exemple : produits/a_classer"
        )
    if source == work_dir or is_relative_to(source, work_dir):
        raise SystemExit(
            "Le dossier source ne doit pas etre le dossier de travail IA. "
            "Utilise un dossier brut separe, par exemple : produits/a_classer"
        )
    if is_relative_to(work_dir, source):
        raise SystemExit(
            "Le dossier source ne doit pas contenir data/classement_ai_work. "
            "Utilise un dossier brut separe, par exemple : produits/a_classer"
        )


def next_reference(target_root: Path, prefix: str, requested_start: int | None) -> int:
    if requested_start is not None:
        return requested_start

    highest = 0
    if target_root.exists():
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
        for path in target_root.iterdir():
            if not path.is_dir():
                continue
            match = pattern.match(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def image_to_data_url(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def make_contact_sheet(images: list[MediaFile], output_path: Path, thumb_size: int = 360) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError as exc:
        raise SystemExit(
            "Pillow est necessaire pour classer les photos. "
            "Installe-le avec : python -m pip install -r requirements-ai.txt"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cols = min(4, max(1, len(images)))
    rows = math.ceil(len(images) / cols)
    label_height = 42
    sheet = Image.new("RGB", (cols * thumb_size, rows * (thumb_size + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    existing_images = [media for media in images if media.path.exists()]
    if not existing_images:
        raise SystemExit("Aucune image encore disponible pour creer la planche contact.")

    for index, media in enumerate(existing_images):
        col = index % cols
        row = index // cols
        x = col * thumb_size
        y = row * (thumb_size + label_height)
        with Image.open(media.path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            left = x + (thumb_size - image.width) // 2
            top = y + (thumb_size - image.height) // 2
            sheet.paste(image, (left, top))
        draw.rectangle((x, y + thumb_size, x + thumb_size, y + thumb_size + label_height), fill="#f2f2f2")
        draw.text((x + 8, y + thumb_size + 10), f"{media.label} - {media.path.name}", fill="black", font=font)

    sheet.save(output_path, "JPEG", quality=88, optimize=True)
    return output_path


def fallback_groups(media_files: list[MediaFile], start: int, prefix: str) -> list[ProductGroup]:
    groups: list[ProductGroup] = []
    images = [media for media in media_files if media.kind == "image"]
    videos = [media for media in media_files if media.kind == "video"]

    for index, image in enumerate(images, start=start):
        reference = f"{prefix}{index:03d}"
        related_videos = [
            video
            for video in videos
            if video.number is not None and image.number is not None and abs(video.number - image.number) <= 1
        ]
        groups.append(
            ProductGroup(
                group_id=f"G{index:03d}",
                reference=reference,
                media=[image, *related_videos],
                name="Article a verifier",
                category="A verifier",
                sub_category="A verifier",
                color="A verifier",
                gender="A verifier",
                brand="A verifier",
                material="A verifier",
                short_description="Article a verifier.",
                description="Description a verifier avant publication.",
                confidence="faible",
                reason="Classement automatique sans IA, base sur le nom ou l'ordre des fichiers.",
            )
        )
    return groups


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


def analyze_images_with_openai(
    image_batch: list[MediaFile],
    videos: list[MediaFile],
    sheet_path: Path,
    use_web_search: bool,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "La librairie openai est necessaire pour le classement IA. "
            "Installe-la avec : python -m pip install -r requirements-ai.txt"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY est manquant dans .env")

    media_index = {
        "images": [{"label": media.label, "filename": media.path.name} for media in image_batch],
        "videos_a_associer_si_evident": [
            {"label": media.label, "filename": media.path.name} for media in videos
        ],
    }

    prompt = f"""
Tu classes des photos de produits pour une boutique WooCommerce.

Chaque image de la planche contact porte une etiquette de type F0001.
Regroupe uniquement les images qui montrent le meme article physique.

Medias disponibles:
{json.dumps(media_index, ensure_ascii=False, indent=2)}

Contraintes strictes:
- Ne mens pas.
- Si tu n'es pas certain, utilise "A verifier".
- Ne donne pas une marque si elle n'est pas visible ou evidente.
- Ne donne pas une pointure/taille si elle n'est pas visible.
- Les videos ne sont pas visibles ici : associe-les seulement si leur nom semble clairement lie au meme produit.
- Reponds uniquement en JSON valide.

Categories autorisees:
- Chaussures
- Vetements
- Pantalons
- Sacs
- Accessoires
- A verifier

Schema attendu:
{{
  "groups": [
    {{
      "group_id": "G001",
      "image_labels": ["F0001", "F0002"],
      "video_labels": [],
      "nom": "nom precis mais prudent",
      "categorie": "Chaussures",
      "sous_categorie": "Sandales",
      "couleur": "Beige",
      "genre": "Femme",
      "marque": "A verifier",
      "matiere": "A verifier",
      "description_courte": "phrase courte",
      "description": "description de 2 a 4 phrases, sans inventer l'etat exact",
      "confiance": "forte|moyenne|faible",
      "raison": "raison courte du regroupement"
    }}
  ]
}}
""".strip()

    content: list[dict[str, str]] = [
        {"type": "input_text", "text": prompt},
        {"type": "input_image", "image_url": image_to_data_url(sheet_path), "detail": "high"},
    ]
    request: dict[str, Any] = {
        "model": os.getenv("OPENAI_MODEL", "gpt-5"),
        "input": [{"role": "user", "content": content}],
        "store": False,
    }
    if use_web_search:
        request["tools"] = [
            {
                "type": os.getenv("OPENAI_WEB_TOOL_TYPE", "web_search_preview"),
                "search_context_size": "low",
            }
        ]

    client = OpenAI()
    response = client.responses.create(**request)
    return parse_json_object(response.output_text)


def build_groups_from_ai(
    media_files: list[MediaFile],
    ai_payloads: list[dict[str, Any]],
    start: int,
    prefix: str,
) -> list[ProductGroup]:
    by_label = {media.label: media for media in media_files}
    used_labels: set[str] = set()
    groups: list[ProductGroup] = []
    current_number = start

    for payload in ai_payloads:
        for raw_group in payload.get("groups", []):
            labels = list(raw_group.get("image_labels", [])) + list(raw_group.get("video_labels", []))
            medias = [by_label[label] for label in labels if label in by_label and label not in used_labels]
            if not medias:
                continue
            for media in medias:
                used_labels.add(media.label)

            reference = f"{prefix}{current_number:03d}"
            current_number += 1
            groups.append(
                ProductGroup(
                    group_id=str(raw_group.get("group_id", reference)),
                    reference=reference,
                    media=medias,
                    name=str(raw_group.get("nom", "Article a verifier")),
                    category=str(raw_group.get("categorie", "A verifier")),
                    sub_category=str(raw_group.get("sous_categorie", "A verifier")),
                    color=str(raw_group.get("couleur", "A verifier")),
                    gender=str(raw_group.get("genre", "A verifier")),
                    brand=str(raw_group.get("marque", "A verifier")),
                    material=str(raw_group.get("matiere", "A verifier")),
                    short_description=str(raw_group.get("description_courte", "Article a verifier.")),
                    description=str(raw_group.get("description", "Description a verifier avant publication.")),
                    confidence=str(raw_group.get("confiance", "faible")),
                    reason=str(raw_group.get("raison", "")),
                )
            )

    for media in media_files:
        if media.label in used_labels:
            continue
        reference = f"{prefix}{current_number:03d}"
        current_number += 1
        groups.append(
            ProductGroup(
                group_id=reference,
                reference=reference,
                media=[media],
                name="Article a verifier",
                category="A verifier",
                sub_category="A verifier",
                color="A verifier",
                gender="A verifier",
                brand="A verifier",
                material="A verifier",
                short_description="Article a verifier.",
                description="Description a verifier avant publication.",
                confidence="faible",
                reason="Media non associe par l'IA.",
            )
        )
    return groups


def destination_name(media: MediaFile, index: int) -> str:
    if media.kind == "image":
        return f"{index:02d}{media.path.suffix.lower()}"
    return f"video_{index:02d}{media.path.suffix.lower()}"


def copy_group_media(groups: list[ProductGroup], target_root: Path) -> None:
    for group in groups:
        folder = target_root / group.reference
        folder.mkdir(parents=True, exist_ok=True)
        image_index = 1
        video_index = 1
        for media in group.media:
            if not media.path.exists():
                print(f"  media introuvable, ignore : {media.path}")
                continue
            if media.kind == "image":
                name = destination_name(media, image_index)
                image_index += 1
            else:
                name = destination_name(media, video_index)
                video_index += 1
            shutil.copy2(media.path, folder / name)


def write_review_csv(path: Path, groups: list[ProductGroup], target_root: Path) -> None:
    rows = []
    for group in groups:
        image_index = 1
        video_index = 1
        for media in group.media:
            if media.kind == "image":
                name = destination_name(media, image_index)
                image_index += 1
            else:
                name = destination_name(media, video_index)
                video_index += 1
            rows.append(
                {
                    "reference": group.reference,
                    "fichier_source": str(media.path),
                    "type_media": media.kind,
                    "fichier_destination": str(target_root / group.reference / name),
                    "groupe_ia": group.group_id,
                    "confiance": group.confidence,
                    "raison": group.reason,
                }
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_products_csv(path: Path, groups: list[ProductGroup]) -> None:
    rows = []
    for group in groups:
        rows.append(
            {
                "reference": group.reference,
                "nom": group.name,
                "categorie": group.category,
                "sous_categorie": group.sub_category,
                "prix": "",
                "stock": "1",
                "etat": "A verifier",
                "couleur": group.color,
                "taille": "",
                "pointure": "A verifier",
                "marque": group.brand,
                "matiere": group.material,
                "genre": group.gender,
                "description_courte": group.short_description,
                "description": group.description,
                "dossier_images": group.reference,
                "statut": "draft",
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def classify_media(args: argparse.Namespace) -> int:
    load_dotenv(args.env)
    validate_source_folder(args)
    media_files = discover_media(args.source)
    images = [media for media in media_files if media.kind == "image"]
    videos = [media for media in media_files if media.kind == "video"]
    start = next_reference(args.target_root, args.prefix, args.start_number)

    print(f"Source : {args.source}")
    print(f"Images trouvees : {len(images)}")
    print(f"Videos trouvees : {len(videos)}")
    print(f"Premiere reference : {args.prefix}{start:03d}")
    print(f"Mode : {'copie reelle' if args.execute else 'controle seulement'}")

    if args.no_ai:
        groups = fallback_groups(media_files, start, args.prefix)
    else:
        payloads = []
        for batch_index in range(0, len(images), args.batch_size):
            batch = images[batch_index : batch_index + args.batch_size]
            sheet_path = args.work_dir / f"contact_sheet_{batch_index // args.batch_size + 1:03d}.jpg"
            make_contact_sheet(batch, sheet_path)
            print(f"Analyse IA : {sheet_path}")
            payloads.append(analyze_images_with_openai(batch, videos, sheet_path, args.web_search))
        groups = build_groups_from_ai(media_files, payloads, start, args.prefix)

    write_review_csv(args.review_csv, groups, args.target_root)
    write_products_csv(args.output_csv, groups)

    if args.execute:
        copy_group_media(groups, args.target_root)

    print("")
    print(f"Groupes produits proposes : {len(groups)}")
    print(f"CSV de controle : {args.review_csv}")
    print(f"CSV WooCommerce : {args.output_csv}")
    if args.execute:
        print(f"Medias copies dans : {args.target_root}")
    else:
        print("Aucune copie effectuee. Relance avec --execute apres verification.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classer automatiquement des photos/videos par produit.")
    parser.add_argument("--source", type=Path, required=True, help="Dossier melange contenant photos et videos.")
    parser.add_argument("--target-root", type=Path, default=Path("produits/images"))
    parser.add_argument("--output-csv", type=Path, default=Path("data/produits_classes_ai.csv"))
    parser.add_argument("--review-csv", type=Path, default=Path("data/classement_medias_ai.csv"))
    parser.add_argument("--work-dir", type=Path, default=Path("data/classement_ai_work"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--prefix", default="CH")
    parser.add_argument("--start-number", type=int)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--execute", action="store_true", help="Copie les medias dans produits/images/REF.")
    parser.add_argument("--no-ai", action="store_true", help="Classe sans IA, uniquement par ordre/nom de fichier.")
    parser.add_argument("--web-search", action="store_true", help="Autorise OpenAI a utiliser la recherche web.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(classify_media(parse_args()))
