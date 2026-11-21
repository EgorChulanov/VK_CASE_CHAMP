"""Card validation and product photos for the local seller catalogue."""

import base64
import binascii
import io
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field


class Card(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0, le=1_000_000)
    stock: int = Field(ge=0, le=100_000)
    pickup: str = Field(max_length=200)
    delivery: int = Field(ge=0, le=10_000)
    days: int = Field(ge=0, le=60)
    post: str = Field(max_length=2000)
    published: bool
    image_data: str | None = Field(default=None, max_length=2_850_000)

    def values(self):
        if not self.title.strip():
            raise HTTPException(422, "Введите название товара")
        if self.published and (
            not self.post.strip() or not (self.pickup.strip() or self.days)
        ):
            raise HTTPException(
                422, "Для публикации добавьте текст записи и способ получения"
            )
        return (
            self.title.strip(),
            self.price,
            self.stock,
            self.pickup.strip(),
            self.delivery,
            self.days,
            self.post.strip(),
            self.published,
        )


class NewCard(Card):
    request_id: str = Field(min_length=8, max_length=100)


class CardEdit(Card):
    version: int = Field(ge=1)


def initialize_media(connection):
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS card_images(product INTEGER PRIMARY KEY REFERENCES products(id), webp BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS new_cards(request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, product INTEGER NOT NULL REFERENCES products(id));
    """)


def prepare_photo(value):
    if value is None:
        return None
    try:
        raw = base64.b64decode(value, validate=True)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("oversize")
        with Image.open(io.BytesIO(raw)) as src:
            if (
                src.format not in ("PNG", "JPEG", "WEBP")
                or src.width * src.height > 12_000_000
            ):
                raise ValueError("unsupported dimensions or format")
            image = ImageOps.exif_transpose(src).convert("RGB")
            image.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.save(out, format="WEBP", quality=87)
            return out.getvalue()
    except (
        binascii.Error,
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
    ) as exc:
        raise HTTPException(
            422, "Выберите JPG, PNG или WebP до 2 МБ и 12 мегапикселей"
        ) from exc


def store_photo(connection, product, photo):
    if photo is not None:
        connection.execute(
            "INSERT INTO card_images(product,webp) VALUES(?,?) ON CONFLICT(product) DO UPDATE SET webp=excluded.webp",
            (product, photo),
        )


def product_photo(connection, product, seller, assets: Path):
    card = connection.execute(
        "SELECT published FROM products WHERE id=?", (product,)
    ).fetchone()
    if not card or (not seller and not card["published"]):
        raise HTTPException(404, "Товар недоступен")
    photo = connection.execute(
        "SELECT webp FROM card_images WHERE product=?", (product,)
    ).fetchone()
    headers = {"Cache-Control": "private, no-cache"}
    if photo:
        return Response(photo["webp"], media_type="image/webp", headers=headers)
    filename = (
        assets / f"cup-{product}.webp"
        if product in (1, 2, 3)
        else assets / "product-default.svg"
    )
    return FileResponse(filename, headers=headers)
