"""미리 받아 둔 덧붙임 자료 (`enrich/`, 006). 화면이 읽기만 한다 — 받는 것은 tools/ 의 스크립트다.

    enrich/<slug>.openalex.json     사람마다 OpenAlex 저자 짝과 대표 논문 셋 (tools/fetch_openalex.py)

**사이트를 굽는 동안 바깥을 부르지 않는다.** 그러면 굽기가 네트워크와 한도에 따라 흔들리고,
사용자 브라우저가 부르면 학회장 와이파이 한 IP 의 하루 한도를 여럿이 나눠 쓴다. 그래서 이
서버에서 미리 받아 저장소에 넣는다.
"""
import json
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=None)
def _load(name):
    try:
        return json.loads((settings.ENRICH_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def openalex(slug):
    """{people.key: {match: {...}|None, works: [...]}}"""
    return _load(f"{slug}.openalex.json").get("people", {})


def text_key(text):
    """번역의 열쇠 — 원문의 sha1 앞 16자. 원문이 바뀌면 열쇠가 바뀌어 낡은 번역이 안 나온다."""
    import hashlib
    return hashlib.sha1((text or "").strip().encode()).hexdigest()[:16]


def languages(slug):
    """미리 번역해 둔 언어들 — enrich/<slug>.<lang>.json (openalex 제외)."""
    out = []
    for p in sorted(settings.ENRICH_DIR.glob(f"{slug}.*.json")):
        lang = p.name[len(slug) + 1:-len(".json")]
        if lang != "openalex":
            out.append(lang)
    return out


def translations(slug, lang):
    """{text_key: 번역}"""
    return _load(f"{slug}.{lang}.json").get("t", {})


def translate(slug, text):
    """{lang: 번역} — 번역이 있는 언어만."""
    if not (text or "").strip():
        return {}
    k = text_key(text)
    return {lang: tr[k] for lang in languages(slug) if (tr := translations(slug, lang)).get(k)}
