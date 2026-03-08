# schemas/classification_schema.py
# Pinned schema version. Increment when any field definition changes.
# All classification records store this version. Never reclassify silently.

SCHEMA_VERSION = "v1"

ALLOWED_THEMES = [
    "Communication",
    "Billing",
    "Professionalism",
    "Responsiveness",
    "Staff",
    "Case Outcome",
    "Process Clarity",
    "Empathy",
    "Office Environment",
    "Value for Money",
    "Documentation",
    "Timeliness",
]

CLASSIFICATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["themes", "overall_sentiment", "confidence", "key_excerpt"],
    "additionalProperties": False,
    "properties": {
        "themes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["name", "polarity", "severity"],
                "additionalProperties": False,
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": ALLOWED_THEMES,
                    },
                    "polarity": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "moderate", "high"],
                    },
                },
            },
        },
        "overall_sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "negative", "mixed"],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "key_excerpt": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
        },
        "flags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}

# Returned when the model fails both attempts. Valid against schema.
FALLBACK_CLASSIFICATION = {
    "themes": [
        {"name": "Communication", "polarity": "neutral", "severity": "low"}
    ],
    "overall_sentiment": "neutral",
    "confidence": 0.0,
    "key_excerpt": "[classification failed — manual review required]",
    "flags": ["classification_failed"],
}
