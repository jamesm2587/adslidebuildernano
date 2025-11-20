from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import requests
from PIL import Image

from src.image_ops import bytes_to_image, ensure_rgba, light_cleanup

LOGGER = logging.getLogger(__name__)
DEFAULT_BASE_URL = "https://api.nano-banana.ai"


@dataclass
class ExtractionResult:
    product_image: Image.Image
    text: Dict[str, str]


class NanoBananaClient:
    def __init__(
        self,
        api_key: Optional[str],
        *,
        base_url: str = DEFAULT_BASE_URL,
        pro_model: str = "nano-banana-pro",
        free_model: str = "nano-banana-lite",
        mock_mode: bool = False,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.pro_model = pro_model
        self.free_model = free_model
        self.timeout = timeout
        self.mock_mode = mock_mode

    def extract_assets(self, image_bytes: bytes) -> ExtractionResult:
        if self.mock_mode or not self.api_key:
            LOGGER.warning("Running Nano Banana client in mock mode; enable API key for production accuracy.")
            return self._mock_extract(image_bytes)

        errors = []
        for model in filter(None, [self.pro_model, self.free_model]):
            try:
                return self._invoke_model(model, image_bytes)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Nano Banana model '%s' failed", model)
                errors.append(f"{model}: {exc}")
        raise RuntimeError("All Nano Banana models failed: " + "; ".join(errors))

    def _invoke_model(self, model: str, image_bytes: bytes) -> ExtractionResult:
        url = f"{self.base_url}/v1/extract"
        payload = {
            "model": model,
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "tasks": ["product_cutout", "ocr"]
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return self._parse_response(data, image_bytes)

    def _parse_response(self, payload: Dict, fallback_bytes: bytes) -> ExtractionResult:
        data = payload.get("data") or payload
        product_image_bytes = self._extract_product_bytes(data) or fallback_bytes
        product_image = light_cleanup(ensure_rgba(bytes_to_image(product_image_bytes)))
        text_fields = data.get("text") or {}
        normalized = {
            "product_name": self._pluck_text(text_fields, "product_name"),
            "price": self._pluck_text(text_fields, "price"),
            "spanish_copy": self._pluck_text(text_fields, "spanish"),
            "english_copy": self._pluck_text(text_fields, "english"),
        }
        return ExtractionResult(product_image=product_image, text=normalized)

    @staticmethod
    def _pluck_text(text_fields: Dict, key: str) -> str:
        value = text_fields.get(key)
        if isinstance(value, dict):
            return value.get("content") or value.get("text") or ""
        return value or ""

    @staticmethod
    def _extract_product_bytes(data: Dict) -> Optional[bytes]:
        keys = [
            "product_cutout_png",
            "product_cutout_base64",
            "product_image_base64",
            "product_image",
        ]
        for key in keys:
            if key not in data:
                continue
            value = data[key]
            if isinstance(value, str):
                if value.strip().startswith("data:image"):
                    value = value.split(",", 1)[-1]
                try:
                    return base64.b64decode(value)
                except base64.binascii.Error:
                    continue
            elif isinstance(value, (bytes, bytearray)):
                return bytes(value)
        return None

    @staticmethod
    def _mock_extract(image_bytes: bytes) -> ExtractionResult:
        source = ensure_rgba(bytes_to_image(image_bytes))
        w, h = source.size
        crop = source.crop((w * 0.1, h * 0.1, w * 0.9, h * 0.9))
        placeholder_text = {
            "product_name": "Sample Product",
            "price": "$9.99",
            "spanish_copy": "Oferta limitada",
            "english_copy": "Limited time offer",
        }
        return ExtractionResult(product_image=light_cleanup(crop), text=placeholder_text)
