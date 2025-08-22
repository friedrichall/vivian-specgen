from __future__ import annotations

INTERACTION_ELEMENTS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "Elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "Type": {"type": "string"},
                    "Name": {"type": "string"}
                },
                "required": ["Type", "Name"],
                "additionalProperties": True
            }
        }
    },
    "required": ["Elements"],
    "additionalProperties": False
}

VISUALIZATION_ELEMENTS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "Elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "Type": {"type": "string"},
                    "Name": {"type": "string"}
                },
                "required": ["Type", "Name"],
                "additionalProperties": True
            }
        }
    },
    "required": ["Elements"],
    "additionalProperties": False
}

STATES_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "States": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "Name": {"type": "string"},
                    "Conditions": {"type": "array"}
                },
                "required": ["Name", "Conditions"],
                "additionalProperties": True
            }
        }
    },
    "required": ["States"],
    "additionalProperties": False
}

TRANSITIONS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "Transitions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "SourceState": {"type": "string"},
                    "DestinationState": {"type": "string"}
                },
                "required": ["SourceState", "DestinationState"],
                "additionalProperties": True
            }
        }
    },
    "required": ["Transitions"],
    "additionalProperties": False
}
