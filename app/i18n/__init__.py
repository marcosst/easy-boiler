import json
from pathlib import Path

SUPPORTED_LANGS = {"en", "pt", "es"}
_DEFAULT_LANG = "pt"

_translations: dict[str, dict[str, str]] = {}

_dir = Path(__file__).parent
for lang in SUPPORTED_LANGS:
    path = _dir / f"{lang}.json"
    with open(path, encoding="utf-8") as f:
        _translations[lang] = json.load(f)


def translate(key: str, lang: str) -> str:
    """Look up a translation key. Falls back to pt, then returns the key itself."""
    if lang in _translations:
        value = _translations[lang].get(key)
        if value is not None:
            return value
    if lang != _DEFAULT_LANG:
        value = _translations[_DEFAULT_LANG].get(key)
        if value is not None:
            return value
    return key
