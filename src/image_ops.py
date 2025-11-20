from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Dict

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.template_manager import TextFieldSpec
DEFAULT_FONT_PATHS = [
    Path("assets/fonts/Inter-Bold.ttf"),
    Path("assets/fonts/Inter-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def bytes_to_image(data: bytes) -> Image.Image:
    """Load an image from raw bytes."""
    return Image.open(io.BytesIO(data)).convert("RGBA")


def ensure_rgba(image: Image.Image) -> Image.Image:
    return image.convert("RGBA") if image.mode != "RGBA" else image


def resize_to_fit(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    image = ensure_rgba(image)
    w, h = image.size
    scale = min(target_w / w, target_h / h)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def paste_centered(base: Image.Image, overlay: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
    overlay = resize_to_fit(overlay, width, height)
    ow, oh = overlay.size
    paste_x = x + (width - ow) // 2
    paste_y = y + (height - oh) // 2
    base.alpha_composite(overlay, dest=(paste_x, paste_y))
    return base


@lru_cache(maxsize=32)
def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in DEFAULT_FONT_PATHS:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap_text(text: str, width: int = 22) -> str:
    if not text:
        return ""
    words = text.strip().split()
    if not words:
        return ""
    lines = []
    current = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= width:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def draw_text_fields(image: Image.Image, text_specs: Dict[str, TextFieldSpec], text_payload: Dict[str, str]) -> Image.Image:
    draw = ImageDraw.Draw(image)
    for key, spec in text_specs.items():
        content = text_payload.get(key)
        if not content:
            continue
        font = _load_font(spec.size)
        wrapped = wrap_text(content, width=20 if key != "price" else len(content) + 4)
        draw.multiline_text((spec.x, spec.y), wrapped, fill=spec.color, font=font, spacing=6)
    return image


def light_cleanup(image: Image.Image) -> Image.Image:
    image = ensure_rgba(image)
    arr = np.array(image)
    if arr.shape[2] == 4:
        alpha = arr[:, :, 3]
    else:
        alpha = np.full(arr.shape[:2], 255, dtype=np.uint8)
    blur = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(radius=2))
    arr[:, :, 3] = np.array(blur)
    return Image.fromarray(arr, mode="RGBA")
