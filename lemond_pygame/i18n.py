"""Tiny JSON-backed localization layer.

Strings live in ``locales/<code>.json`` as flat key -> template maps. Call
:func:`load_locales` once at startup, switch with :func:`set_locale`, and look up
text with :func:`t`. Missing keys fall back to English and then to the raw key,
so the game never crashes on a typo.
"""

from __future__ import annotations

import json

from .respath import resource_path

AVAILABLE = ["en", "ru"]
LOCALE_NAMES = {"en": "English", "ru": "Русский"}

_locales: dict[str, dict[str, str]] = {}
_current = "en"


def load_locales() -> None:
    for code in AVAILABLE:
        with open(resource_path("locales", f"{code}.json"), encoding="utf-8") as f:
            _locales[code] = json.load(f)


def set_locale(code: str) -> None:
    global _current
    if code in AVAILABLE:
        _current = code


def get_locale() -> str:
    return _current


def next_locale(code: str | None = None) -> str:
    cur = code if code is not None else _current
    idx = AVAILABLE.index(cur) if cur in AVAILABLE else 0
    return AVAILABLE[(idx + 1) % len(AVAILABLE)]


def t(key: str, **kwargs) -> str:
    table = _locales.get(_current) or {}
    template = table.get(key)
    if template is None:
        template = (_locales.get("en") or {}).get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template
    return template


# --- Display helpers for core data objects (presentation only) ---


def item_name(item) -> str:
    unique = getattr(item, "unique", "")
    if unique:  # named gold artifact; its own name, not the affix-suffix scheme
        return t("artifact." + unique + ".name")
    base = f"{t('item.' + item.kind)} {item.tier}"
    affixes = list(getattr(item, "affixes", ()))
    # Genitive-style suffixes ("Sword 3 of Sharpness" / "Меч 3 остроты") keep the
    # Russian rendering free of adjective gender agreement.
    if len(affixes) == 1:
        return t("item.affix1", name=base, a=t("affix." + affixes[0]))
    if len(affixes) >= 2:
        return t("item.affix2", name=base, a=t("affix." + affixes[0]), b=t("affix." + affixes[1]))
    return base


def item_describe(item) -> str:
    slot = item.slot or t("item.misc")
    return t("item.describe", name=item_name(item), slot=slot, power=item.power)


def monster_name(creature) -> str:
    return t("monster." + creature.kind)


def class_name(class_kind: str) -> str:
    return t("class." + class_kind)
