from __future__ import annotations

import io
import os
from typing import Dict

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from src.image_ops import draw_text_fields, paste_centered
from src.nano_banana import ExtractionResult, NanoBananaClient
from src.template_manager import TemplateManager

load_dotenv()

st.set_page_config(page_title="Nano Banana Ad Converter", layout="wide")


@st.cache_resource
def get_template_manager() -> TemplateManager:
    return TemplateManager()


@st.cache_resource
def get_banana_client() -> NanoBananaClient:
    secrets_cfg = st.secrets["banana"] if "banana" in st.secrets else {}
    api_key = secrets_cfg.get("api_key") or os.getenv("BANANA_API_KEY")
    base_url = secrets_cfg.get("base_url") or os.getenv("BANANA_BASE_URL")
    pro_model = secrets_cfg.get("pro_model") or os.getenv("BANANA_PRO_MODEL") or "nano-banana-pro"
    free_model = secrets_cfg.get("free_model") or os.getenv("BANANA_FREE_MODEL") or "nano-banana-lite"
    env_mock = os.getenv("BANANA_MOCK_MODE", "").lower() in {"1", "true", "yes"}
    mock_mode = bool(secrets_cfg.get("mock_mode", False)) or env_mock
    return NanoBananaClient(
        api_key=api_key,
        base_url=base_url or "https://api.nano-banana.ai",
        pro_model=pro_model,
        free_model=free_model,
        mock_mode=mock_mode,
    )


def build_slide(template_id: str, extraction: ExtractionResult, text_payload: Dict[str, str]):
    manager = get_template_manager()
    template = manager.load_image(template_id).copy()
    spec = manager.get(template_id)
    x, y, width, height = spec.product_area
    canvas = paste_centered(template, extraction.product_image, x, y, width, height)
    canvas = draw_text_fields(canvas, spec.text_fields, text_payload)
    return canvas.convert("RGB")


def image_to_bytes(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_text_form(extracted: Dict[str, str]) -> Dict[str, str]:
    st.subheader("Text fields")
    col_a, col_b = st.columns(2)
    with col_a:
        product_name = st.text_input("Product name", value=extracted.get("product_name", ""))
        spanish_copy = st.text_area("Spanish copy", value=extracted.get("spanish_copy", ""), height=100)
    with col_b:
        price = st.text_input("Price", value=extracted.get("price", ""))
        english_copy = st.text_area("English copy", value=extracted.get("english_copy", ""), height=100)
    return {
        "product_name": product_name.strip(),
        "price": price.strip(),
        "spanish_copy": spanish_copy.strip(),
        "english_copy": english_copy.strip(),
    }


def main() -> None:
    st.title("Ad-to-Template Converter")
    st.caption("Upload a premade JPG ad and rebuild it on a 1080×1920 template using Nano Banana extractors.")

    manager = get_template_manager()
    templates = manager.available_templates()
    template_labels = {spec.name: spec.id for spec in templates}

    with st.sidebar:
        st.header("Input")
        selected_store = st.selectbox("Store template", list(template_labels.keys()))
        template_id = template_labels[selected_store]
        preview_img = manager.load_image(template_id).copy()
        preview_img.thumbnail((320, 580), Image.Resampling.LANCZOS)
        st.image(preview_img, caption="Template preview", use_container_width=True)
        uploaded_file = st.file_uploader("Upload JPG ad", type=["jpg", "jpeg"])
        process_clicked = st.button("Extract & Build", use_container_width=True, disabled=uploaded_file is None)

    if "extraction" not in st.session_state:
        st.session_state["extraction"] = None
    if "composed" not in st.session_state:
        st.session_state["composed"] = None
    if "text_fields" not in st.session_state:
        st.session_state["text_fields"] = {}

    if process_clicked and uploaded_file is not None:
        client = get_banana_client()
        try:
            with st.spinner("Extracting product and copy with Nano Banana..."):
                extraction = client.extract_assets(uploaded_file.getvalue())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Extraction failed: {exc}")
            return
        st.session_state["extraction"] = extraction
        st.session_state["text_fields"] = extraction.text
        composed = build_slide(template_id, extraction, extraction.text)
        st.session_state["composed"] = composed

    extraction: ExtractionResult | None = st.session_state.get("extraction")
    composed_image = st.session_state.get("composed")

    if extraction is None:
        st.info("Upload an ad and click Extract & Build to begin.")
        return

    st.markdown("---")
    col_preview, col_controls = st.columns([2, 1])

    with col_controls:
        st.image(extraction.product_image, caption="Product cut-out", use_container_width=True)
        edited_text = render_text_form(st.session_state.get("text_fields", {}))
        if edited_text != st.session_state.get("text_fields"):
            st.session_state["text_fields"] = edited_text
        if st.button("Refresh Preview", use_container_width=True):
            composed_image = build_slide(template_id, extraction, edited_text)
            st.session_state["composed"] = composed_image

    with col_preview:
        if composed_image is not None:
            st.image(composed_image, caption="1080×1920 output", use_container_width=True)
            download_data = image_to_bytes(composed_image)
            st.download_button(
                "Download final PNG",
                data=download_data,
                file_name="nano-banana-slide.png",
                mime="image/png",
                use_container_width=True,
            )
        else:
            st.warning("Click Refresh Preview to render the current text values.")

    with st.expander("Debug payload", expanded=False):
        st.json({"text": st.session_state.get("text_fields"), "template": selected_store})


if __name__ == "__main__":
    main()
