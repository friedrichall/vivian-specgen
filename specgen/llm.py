from __future__ import annotations
import json
from typing import Dict, Any, Optional
from openai import OpenAI

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
    return t

class LLMClient:
    def __init__(self, *, model: str, api_key: str, base_url: Optional[str] = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _chat_json_mode(self, system: str, user: str) -> str:
        """
        Primärer Pfad: Chat Completions mit JSON-Mode (response_format={"type":"json_object"}).
        Fällt automatisch zurück, falls dein SDK den Parameter noch nicht kennt.
        """
        messages = [
            {"role": "system", "content": "Antworte ausschließlich mit einem einzelnen JSON-Objekt. Keine Erklärungen."},
            {"role": "user", "content": user},
        ]
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0
            )
        except TypeError:
            # Ältere SDKs: ohne response_format, aber mit harter Instruktion
            messages = [
                {"role": "system", "content": "Gib ausschließlich JSON aus (ein einzelnes Objekt), ohne Text oder Code-Fences."},
                {"role": "user", "content": user + "\n\nWICHTIG: Nur JSON, strikt am Schema orientieren."},
            ]
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0
            )
        return resp.choices[0].message.content or "{}"

    def generate_json(self, *, system: str, user: str, schema: Dict[str, Any], name: str) -> Dict[str, Any]:
        """
        Erzwingt JSON-only via Chat Completions.
        Das Schema wird in den Prompt gepackt; Validierung/Korrektur macht dein generator.py.
        """
        # Schema + Aufgabe in den User-Prompt mischen (Responses API fällt weg)
        prompt = (
            f"{system}\n\n"
            f"Du MUSST ein einzelnes JSON-Objekt liefern, ohne Code-Fences und ohne Erklärungen.\n"
            f"Es MUSS exakt der folgenden JSON-Top-Level-Struktur entsprechen (jsonschema):\n"
            f"{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"Aktuelle Datei ({name}):\n{user}\n"
        )

        raw = self._chat_json_mode(system, prompt)
        text = _strip_code_fences(raw)
        return json.loads(text)
