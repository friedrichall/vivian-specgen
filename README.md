# SpecGen (No-CLI) – One-Click in PyCharm

Ein klares Python-Projekt ohne CLI-Parameter. Du setzt nur einmal den `OPENAI_API_KEY` in `settings.py` und drückst **Run** auf `app.py`.

## Schritte
1) `pip install -r requirements.txt`
2) In `settings.py` den Key eintragen (`OPENAI_API_KEY = "sk-..."`).
3) `app.py` starten (Run/Debug).

Ergebnis: Die vier Dateien (**InteractionElements.json**, **VisualizationElements.json**, **States.json**, **Transitions.json**) + **USAGE.md** werden in `build/FunctionalSpecification` erzeugt.
