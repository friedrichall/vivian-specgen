from __future__ import annotations
import json, pathlib
from typing import Dict, Any, Tuple
from jsonschema import validate, ValidationError
from .schemas import (
    INTERACTION_ELEMENTS_SCHEMA,
    VISUALIZATION_ELEMENTS_SCHEMA,
    STATES_SCHEMA,
    TRANSITIONS_SCHEMA,
)
from .llm import LLMClient

SYSTEM_PROMPT = """Du bist ein strenger Konfigurator für Vivian-Prototypen.
Halte dich 1:1 an das vorgegebene JSON-Schema (strict) und an die bereitgestellten Dokus.
Keine Erklärungen, nur das reine JSON nach Schema.
"""

FILE_ORDER: Tuple[Tuple[str, Dict[str, Any]], ...] = (
    ("InteractionElements.json", INTERACTION_ELEMENTS_SCHEMA),
    ("VisualizationElements.json", VISUALIZATION_ELEMENTS_SCHEMA),
    ("States.json", STATES_SCHEMA),
    ("Transitions.json", TRANSITIONS_SCHEMA),
)

def _build_user_prompt(spec_text: str, docs_text: str, target_file: str) -> str:
    return f"""
Ziel-Datei: {target_file}

Aufgabe: Erzeuge ausschließlich die JSON-Inhalte für die Datei oben.
Projekt-Spezifikation:
---
{spec_text}
---

Auszüge aus den offiziellen Dokus und Beispielen (als Referenz, nur relevante Teile verwenden):
---
{docs_text}
---
"""

def _validate_or_repair(client: LLMClient, data: Dict[str, Any], schema: Dict[str, Any], system: str, user: str, name: str, max_repairs: int = 2) -> Dict[str, Any]:
    from jsonschema import ValidationError
    for attempt in range(max_repairs + 1):
        try:
            validate(instance=data, schema=schema)
            return data
        except ValidationError as e:
            if attempt == max_repairs:
                raise
            repair_user = user + f"\n\nFEHLER: {str(e)}\nBitte korrigiere das JSON und liefere nur korrektes JSON."
            data = client.generate_json(system=system, user=repair_user, schema=schema, name=name)
    return data

def generate_all(*, spec_text: str, docs_text: str, out_dir: str, model: str, api_key: str, base_url: str | None) -> Dict[str, Any]:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    client = LLMClient(model=model, api_key=api_key, base_url=base_url)

    results: Dict[str, Any] = {}

    for filename, schema in FILE_ORDER:
        user = _build_user_prompt(spec_text, docs_text, filename)
        data = client.generate_json(system=SYSTEM_PROMPT, user=user, schema=schema, name=filename.replace(".json",""))
        data = _validate_or_repair(client, data, schema, SYSTEM_PROMPT, user, filename.replace(".json",""))
        (out / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")
        results[filename] = data

    usage = f"""# Verwendung

Lege die vier Dateien in den *FunctionalSpecification*-Ordner deines Prototyps:

- InteractionElements.json
- VisualizationElements.json
- States.json
- Transitions.json

Starte anschließend das Projekt, der Loader liest die Dateien automatisch gemäß der vorgegebenen Struktur ein.
"""
    (out.parent / "USAGE.md").write_text(usage, encoding="utf-8")
    return results
