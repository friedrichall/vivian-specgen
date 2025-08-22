#!/usr/bin/env python3
"""Generate an interaction specification from Unity input and run the pipeline.

Unity calls this script with a natural language description of the
interaction followed by pairs of ``<object-name> <interaction-type>`` for
all selected interaction objects.  From this information an LLM generates a
Vivian YAML specification which is then passed to the pipeline implemented
in :mod:`app.py`.
"""

from pathlib import Path
import sys

from openai import OpenAI

from app import main as run_pipeline
from settings import BASE_URL, MODEL, OPENAI_API_KEY, SPEC_PATH


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
    return t


def generate_spec(description: str, objects: dict[str, str]) -> str:
    """Use an LLM to create the YAML specification text."""
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)

    sample_path = Path(__file__).parent / "project" / "specs" / "cube_touch_red.yml"
    example = sample_path.read_text(encoding="utf-8") if sample_path.exists() else ""

    object_lines = "\n".join(f"{name}: {typ}" for name, typ in objects.items())
    user_prompt = (
        "Erzeuge eine Vivian Interaktionsspezifikation im YAML-Format.\n"
        f"Beschreibung: {description}\n"
        "Interaktionsobjekte und Typen:\n"
        f"{object_lines}\n"
        "Nutze exakt die Struktur wie im folgenden Beispiel:\n"
        f"{example}\n"
        "Gib nur YAML ohne Erklärungen aus."
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Du erzeugst Vivian-Spezifikationen. Nur YAML ausgeben."},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    return _strip_code_fences(resp.choices[0].message.content or "")


def main() -> None:
    description = sys.argv[1] if len(sys.argv) > 1 else ""
    args = sys.argv[2:]
    object_interactions = {args[i]: args[i + 1] for i in range(0, len(args), 2)}

    print("Unity Connector:\n______________________________\n")
    print("description:", description)
    for name, element in object_interactions.items():
        print(f"{name}: {element}")

    if OPENAI_API_KEY.startswith("sk-REPLACE_ME"):
        print("⚠️ Bitte zuerst den OPENAI_API_KEY in settings.py setzen.")
        sys.exit(1)

    spec_text = generate_spec(description, object_interactions)
    spec_path = Path(SPEC_PATH)
    spec_path.write_text(spec_text, encoding="utf-8")
    print(f"📄 Spezifikation gespeichert unter: {spec_path.resolve()}")

    run_pipeline()


if __name__ == "__main__":
    main()

