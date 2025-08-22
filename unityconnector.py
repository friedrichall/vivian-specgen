#!/usr/bin/env python3
"""Generate an interaction specification from Unity input and run the pipeline.

Unity calls this script with:
  1) group name (argv[1])                <-- added
  2) natural language description (argv[2])
  3) pairs of:  <object-name> <interaction-type>  (argv[3:])

Example:
  python unityconnector.py "cube_touch_red" "Wuerfel wird bei Touch rot" Cube_Default AppearingObject Cube_Red AppearingObject CubeTouch TouchArea

If the group name is not passed (legacy call), the script falls back to:
  group = "GeneratedGroup", description = argv[1], pairs start at argv[2].
"""

from pathlib import Path
import sys
import io
import textwrap
from typing import Dict

from openai import OpenAI

# We bypass app.main and call the generator directly so we can control the output folder by group name.
from specgen.generator import generate_all
from settings import BASE_URL, MODEL, OPENAI_API_KEY


# -------------------------------
# Encoding-safe console output
# -------------------------------

def _prepare_console() -> None:
    """Make stdout/stderr robust on Windows consoles (no Unicode crashes)."""
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=sys.stdout.encoding or "utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=sys.stderr.encoding or "utf-8", errors="replace")
        except Exception:
            pass


# -------------------------------
# Helpers
# -------------------------------

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
    return t.strip()


def _load_docs() -> str:
    """Load local documentation (Vivian docs and project README) for grounding."""
    here = Path(__file__).parent
    docs_dir = here / "specgen" / "docs"
    chunks = []

    proj_readme = here / "README.md"
    if proj_readme.exists():
        chunks.append("==== PROJECT_README.md ====")
        chunks.append(proj_readme.read_text(encoding="utf-8"))

    ordered = [
        "README.md",
        "InteractionElementsDocu.md",
        "VisualizationElementsDocu.md",
        "StatesDocu.md",
        "TransitionsDocu.md",
    ]
    for name in ordered:
        p = docs_dir / name
        if p.exists():
            chunks.append(f"==== {name} ====")
            chunks.append(p.read_text(encoding="utf-8"))

    return "\n".join(chunks)


def _build_prompt(description: str, objects: Dict[str, str], example_yaml: str, docs_bundle: str) -> str:
    """Explain Vivian, define the YAML structure, include docs & example."""
    object_lines = "\n".join(f"{name}: {typ}" for name, typ in objects.items()) or "(keine Objekt-Typen uebergeben)"

    yaml_template = textwrap.dedent("""
    # TEMPLATE FOR THE VIVIAN YAML SPEC (no comments in final output!)
    name: <kurzer_titel_der_interaktion>
    objects:
      <visual_object_name>: <kurzer_hinweis_appearingobject_etc>
      # Beispiel:
      # Cube_Default: AppearingObject visible by default
      # Cube_Red: AppearingObject hidden by default

    interactions:
      - type: <InteractionElementType>   # z.B. TouchArea
        name: <InteractionElementName>   # z.B. CubeTouch
        plane: {x: 0, y: 0, z: 1}        # wenn relevant
        resolution: {x: 256, y: 256}     # wenn relevant

    states:
      - name: <state_name_1>             # z.B. idle.state
        show:
          <VisualizationElementName1>: <float 0.0..1.0>
          <VisualizationElementName2>: <float 0.0..1.0>
      - name: <state_name_2>             # z.B. touched.state
        show:
          <...>: <...>

    transitions:
      - from: <state_name_src>           # z.B. idle.state
        via: {element: <InteractionElementName>, event: <EVENT>}   # z.B. TOUCH_START
        to: <state_name_dst>             # z.B. touched.state
      - from: <state_name_src_2>
        via: {element: <InteractionElementName>, event: <EVENT>}   # z.B. TOUCH_END
        to: <state_name_dst_2>
    """).strip()

    rules = textwrap.dedent("""
    SPIELREGELN (WICHTIG):
    - Gib ausschliesslich YAML zurueck (kein Markdown, keine Code-Fences, keine Erklaerungen, keine Kommentare).
    - Verwende exakt die Top-Level-Schluessel: name, objects, interactions, states, transitions.
    - Benutze nur Interaction/Visualization/State/Transition-Konzepte, die in den beigefuegten Vivian-Dokumenten definiert sind.
    - Fuer Sichtbarkeitsumschaltungen nutze AppearingObject (ueber Floatwerte 0.0/1.0 in states.show); direkter Materialfarbwechsel ist nicht vorgesehen.
    - Events in transitions sind die in den Vivian-Docs definierten, z. B. TOUCH_START, TOUCH_END (falls passend).
    - Objekt-/Elementnamen muessen konsistent sein (z. B. Cube_Default/Cube_Red/CubeTouch).
    - states.show belegt fuer jedes relevante VisualizationElement einen Float (0.0 = aus, 1.0 = an).
    - Halte die YAML-Struktur formal moeglichst nah am Beispiel und am Template.
    """)

    vivian_description = textwrap.dedent("""
    VIVIAN (Kurzbeschreibung):
    Vivian ist ein konfigurationsgetriebenes Framework fuer Interaktionen/Visualisierungen.
    Ein Prototyp laedt vier JSON-Dateien (InteractionElements.json, VisualizationElements.json, States.json, Transitions.json).
    Das hier zu erzeugende YAML ist eine kompakte Spezifikation, aus der die Pipeline diese vier JSON-Dateien generiert.
    - InteractionElements.json: Interaktionsflaechen/-elemente (z. B. TouchArea mit Plane/Resolution)
    - VisualizationElements.json: Visualisierungselemente (z. B. AppearingObject, Name wie im 3D-Modell)
    - States.json: Zustaende und Sichtbarkeit (FloatValueVisualization)
    - Transitions.json: Zustandswechsel, getriggert von InteractionElements (z. B. TOUCH_START/TOUCH_END)
    """)

    prompt = textwrap.dedent(f"""
    Erzeuge eine Vivian Interaktionsspezifikation im YAML-Format fuer die folgende Unity-Szene.

    BESCHREIBUNG (Natuerliche Sprache):
    ---
    {description}
    ---

    SZENEN-OBJEKTE (Name -> Interaction-Element-Typ):
    ---
    {object_lines}
    ---

    WAS IST VIVIAN? / DATEIEN:
    {vivian_description}

    YAML-STRUKTUR (nur YAML ausgeben, KEINE Kommentare):
    ---
    {yaml_template}
    ---

    REGELN:
    {rules}

    DOKUMENTE (Ground Truth):
    ---
    {docs_bundle}
    ---

    REFERENZBEISPIEL:
    ---
    {example_yaml}
    ---

    WICHTIG: Nur die fertige Vivian-YAML-Spezifikation ausgeben
    (ohne Markdown, ohne Erklaerungen, ohne Code-Fences).
    """).strip()

    return prompt


def _parse_argv(argv: list[str]) -> tuple[str, str, Dict[str, str]]:
    """Parse CLI with group name support.
    New style:  argv = [group, description, obj1, type1, obj2, type2, ...]
    Legacy:     argv = [description, obj1, type1, ...]   -> group="GeneratedGroup"
    """
    if not argv:
        return "GeneratedGroup", "", {}

    if len(argv) >= 3 and (len(argv) - 2) % 2 == 0:
        group = argv[0]
        description = argv[1]
        pairs = argv[2:]
    else:
        # legacy
        group = "GeneratedGroup"
        description = argv[0]
        pairs = argv[1:]

    if len(pairs) % 2 != 0:
        # make even
        pairs = pairs[:-1]

    objects = {pairs[i]: pairs[i + 1] for i in range(0, len(pairs), 2)}
    return group, description, objects


def generate_spec(description: str, objects: Dict[str, str]) -> str:
    """Use an LLM to create the Vivian YAML specification text."""
    if not description and not objects:
        raise ValueError("Es wurden weder Beschreibung noch Objekte uebergeben – bitte mindestens eins angeben.")

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)

    sample_path = Path(__file__).parent / "project" / "specs" / "cube_touch_red.yml"
    example = sample_path.read_text(encoding="utf-8") if sample_path.exists() else ""

    docs_bundle = _load_docs()
    user_prompt = _build_prompt(description, objects, example, docs_bundle)

    # Chat Completions; YAML-only via instructions
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein strenger Konfigurator fuer das Vivian-Framework. "
                    "Gib ausschliesslich YAML aus, das exakt der geforderten Struktur entspricht. "
                    "Kreiere keine neuen, undokumentierten Konzepte. "
                    "Wenn Informationen fehlen, triff konservative, dokumentkonforme Annahmen."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    yaml_text = _strip_code_fences(resp.choices[0].message.content or "")
    if not any(k in yaml_text for k in ("\nobjects:", "\ninteractions:", "\nstates:", "\ntransitions:")):
        print("Hinweis: YAML wirkt ungewoehnlich (Top-Level fehlt). Die Pipeline versucht Validation/Repair.")
    return yaml_text


# -------------------------------
# Main entry
# -------------------------------

def main() -> None:
    _prepare_console()

    if OPENAI_API_KEY.startswith("sk-REPLACE_ME"):
        print("Bitte zuerst den OPENAI_API_KEY in settings.py setzen.")
        sys.exit(1)

    # Parse arguments from Unity
    argv = sys.argv[1:]
    group, description, object_interactions = _parse_argv(argv)

    print("Unity -> Vivian Connector")
    print("______________________________")
    print("Group:", group or "(leer)")
    print("Beschreibung:", description or "(leer)")
    for name, element in object_interactions.items():
        print(f"{name}: {element}")

    # Generate Vivian YAML from NL description + objects
    spec_text = generate_spec(description, object_interactions)

    # Compute Unity project paths (relative to Unity's working directory)
    # Output locations under the group folder:
    #   Packages/vivian-example-prototypes/Resources/<group>/<group>.yml
    #   Packages/vivian-example-prototypes/Resources/<group>/FunctionalSpecification/*.json
    unity_root = Path.cwd()
    group_dir = unity_root / "Packages" / "vivian-example-prototypes" / "Resources" / group
    fs_dir = group_dir / "FunctionalSpecification"
    group_dir.mkdir(parents=True, exist_ok=True)
    fs_dir.mkdir(parents=True, exist_ok=True)

    # Write the YAML spec into the group folder
    spec_path = group_dir / f"{group}.yml"
    spec_path.write_text(spec_text, encoding="utf-8")
    print("")
    print("OK: Spezifikation gespeichert unter:", str(spec_path))

    # Prepare docs (same bundle that guides the model) for the generator
    docs_bundle = _load_docs()

    # Run the generator directly so we can set out_dir = group-specific FunctionalSpecification
    # Note: generate_all() handles JSON-schema validation + repair loop.
    print("")
    print("Starte Pipeline zur Generierung der vier JSON-Dateien ...")
    _ = generate_all(
        spec_text=spec_text,
        docs_text=docs_bundle,
        out_dir=str(fs_dir),
        model=MODEL,
        api_key=OPENAI_API_KEY,
        base_url=BASE_URL,
    )

    print("OK: Dateien erzeugt in:", str(fs_dir))
    print("   - InteractionElements.json")
    print("   - VisualizationElements.json")
    print("   - States.json")
    print("   - Transitions.json")
    print("   - USAGE.md (eine Ebene darueber)")
    # Note: USAGE.md wird in fs_dir.parent (= group_dir) geschrieben.
    # Das kommt aus generate_all(), damit die Anleitung klar zum Group-Ordner passt.


if __name__ == "__main__":
    main()
