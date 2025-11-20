from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image


@dataclass(frozen=True)
class TextFieldSpec:
    x: int
    y: int
    size: int
    color: str


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    name: str
    template_path: Path
    product_area: Tuple[int, int, int, int]
    text_fields: Dict[str, TextFieldSpec]


class TemplateManager:
    """Loads and serves template metadata plus PIL images."""

    def __init__(self, config_path: Path | str = "config/templates.json") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Template config not found at {self.config_path}")
        self._templates: Dict[str, TemplateSpec] = {}
        self._load_config()

    def _load_config(self) -> None:
        raw = json.loads(self.config_path.read_text())
        stores = raw.get("stores", [])
        for entry in stores:
            text_fields = {
                key: TextFieldSpec(**value) for key, value in entry.get("text_fields", {}).items()
            }
            product_area = entry.get("product_area", {})
            area_tuple = (
                int(product_area.get("x", 0)),
                int(product_area.get("y", 0)),
                int(product_area.get("width", 0)),
                int(product_area.get("height", 0)),
            )
            spec = TemplateSpec(
                id=entry["id"],
                name=entry.get("name", entry["id"]).strip(),
                template_path=Path(entry["template_path"]),
                product_area=area_tuple,
                text_fields=text_fields,
            )
            self._templates[spec.id] = spec

    def available_templates(self) -> List[TemplateSpec]:
        return list(self._templates.values())

    def get(self, template_id: str) -> TemplateSpec:
        if template_id not in self._templates:
            raise KeyError(f"Unknown template '{template_id}'")
        return self._templates[template_id]

    def load_image(self, template_id: str) -> Image.Image:
        spec = self.get(template_id)
        template_path = spec.template_path
        if not template_path.exists():
            raise FileNotFoundError(f"Template image missing: {template_path}")
        return Image.open(template_path).convert("RGBA")
