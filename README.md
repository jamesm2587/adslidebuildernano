# Ad Slide Builder (Nano Banana)

Streamlit app that converts a premade 1080p JPG advertisement into a polished 1080 × 1920 template-ready slide using Nano Banana Pro (or the free tier when Pro is unavailable).

## Features
- Drag-and-drop JPG upload plus store selector that auto-loads the matching template (see `config/templates.json`).
- Nano Banana client tries the Pro model first, then falls back to the free tier; a mock mode keeps development unblocked without an API key.
- Automatic extraction of the product cut-out and visible text (product title, price, Spanish + English copy) directly from the uploaded ad.
- Smart placement of the cut-out inside template-specific bounding boxes with aspect-ratio-safe scaling and light edge smoothing only.
- Text fields are redrawn inside the template with editable forms so you can tweak wording before exporting.
- Instant preview plus downloadable 1080 × 1920 PNG that is ready for publishing.

## Getting Started

1. **Python environment**
   ```bash
   cd /workspace
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Secrets / API keys**
   - Copy the template and fill in your credentials:
     ```bash
     cp .streamlit/secrets.toml.example .streamlit/secrets.toml
     ```
   - Populate the `[banana]` block with your Nano Banana Pro API key.  
   - If you need to keep secrets outside the repo, set env vars instead: `BANANA_API_KEY`, `BANANA_BASE_URL`, `BANANA_PRO_MODEL`, `BANANA_FREE_MODEL`, `BANANA_MOCK_MODE`.

3. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

## Usage Notes
- Upload a JPG ad and click **Extract & Build**. The app calls Nano Banana; when Pro fails it automatically retries with the free model.
- The extracted product cut-out and text will appear on the right; adjust any text fields and click **Refresh Preview** to rebuild the slide.
- Click **Download final PNG** once you are satisfied. Output is always 1080 × 1920.
- Template assets live in `assets/templates/` and are configured via `config/templates.json`. Adjust the bounding boxes/text styles there to add new stores.

## Security
- Never hard-code API keys. Use `.streamlit/secrets.toml` (excluded from git) or environment variables.
- Mock mode (`mock_mode = true` in secrets or `BANANA_MOCK_MODE=1`) keeps the UI working without hitting the Nano Banana endpoints, though extraction quality is limited.
