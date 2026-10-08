"""제1저자·교신저자 고르기 (005·006). 뷰와 `tools/fetch_openalex.py` 가 같이 쓴다.

모델이 아니라 **자료의 꼴**(authors · affiliations 리스트, 발표자 문자열)을 받는다 —
수집 스크립트는 DB 없이 `conferences/<slug>.json` 을 읽기 때문이다. 두 곳이 사람을 다르게
고르면 미리 받은 논문 목록이 화면의 사람과 어긋난다.
"""
import re
import unicodedata

_HONORIFIC = re.compile(r"^(Prof\.?|Professor|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+", re.I)
SPEAKER_KINDS = ("talk", "plenary", "keynote", "poster")


def clean(name):
    """직함·괄호를 뗀 이름. "Prof. A B (Convener: C)" → "A B"."""
    return _HONORIFIC.sub("", re.sub(r"\s*\(.*?\)", "", name or "")).strip(" ,;*")


def norm(name):
    """비교용 — 악센트·하이픈·점·대소문자·띄어쓰기를 지운다. "Kyung-Sik Choi" == "Kyungsik Choi"."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", s.lower())


def key(name, affiliation):
    """미리 받은 자료(enrich/<slug>.openalex.json)의 열쇠."""
    return f"{norm(name)}|{(affiliation or '').strip().lower()}"


def pick(authors, affiliations, speaker="", kind="talk"):
    """[{name, roles: ["1st author", "corresponding"], affiliation}].

    초록이 있으면 제1저자와 교신저자(같은 사람이면 한 줄에 역할 둘), 없으면 발표자.
    """
    out = []
    affiliations = affiliations or []

    def add(name, role, affiliation=""):
        name = clean(name)
        if not name:
            return
        hit = next((p for p in out if norm(p["name"]) == norm(name)), None)
        if hit:
            if role not in hit["roles"]:
                hit["roles"].append(role)
            hit["affiliation"] = hit["affiliation"] or affiliation
        else:
            out.append({"name": name, "roles": [role], "affiliation": affiliation})

    def affil_of(author):
        refs = author.get("affiliations") or []
        return "; ".join(affiliations[r - 1] for r in refs
                         if isinstance(r, int) and 0 < r <= len(affiliations))

    if authors:
        add(authors[0].get("name"), "1st author", affil_of(authors[0]))
        for a in authors:
            if a.get("corresponding"):
                add(a.get("name"), "corresponding", affil_of(a))
    elif kind in SPEAKER_KINDS:
        add(speaker, "speaker")
    return out
