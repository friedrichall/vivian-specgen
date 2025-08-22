from __future__ import annotations
from pathlib import Path
import sys
from settings import OPENAI_API_KEY, BASE_URL, MODEL, SPEC_PATH, OUT_DIR
from specgen.generator import generate_all

def main():
    if OPENAI_API_KEY.startswith("sk-REPLACE_ME"):
        print("⚠️ Bitte zuerst den OPENAI_API_KEY in settings.py setzen.")
        sys.exit(1)

    # Read spec
    spec_path = Path(SPEC_PATH)
    if not spec_path.exists():
        print(f"❌ Spezifikation nicht gefunden: {spec_path.resolve()}")
        sys.exit(2)
    spec_text = spec_path.read_text(encoding="utf-8")

    # Bundle docs shipped with the repo
    docs_dir = Path(__file__).parent / "specgen" / "docs"
    doc_texts = []
    for p in ["README.md", "InteractionElementsDocu.md", "VisualizationElementsDocu.md", "StatesDocu.md", "TransitionsDocu.md"]:
        f = docs_dir / p
        if f.exists():
            doc_texts.append(f"==== {p} ====")
            doc_texts.append(f.read_text(encoding='utf-8'))
    docs_text = "\n".join(doc_texts)

    results = generate_all(
        spec_text=spec_text,
        docs_text=docs_text,
        out_dir=OUT_DIR,
        model=MODEL,
        api_key=OPENAI_API_KEY,
        base_url=BASE_URL,
    )

    print("✅ Fertig! Dateien wurden erzeugt in:", Path(OUT_DIR).resolve().parent)
    print("   - InteractionElements.json")
    print("   - VisualizationElements.json")
    print("   - States.json")
    print("   - Transitions.json")
    print("   - USAGE.md")

if __name__ == "__main__":
    main()
