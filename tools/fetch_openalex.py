#!/usr/bin/env python3
"""학회의 제1저자·교신저자마다 OpenAlex 에서 저자를 짝짓고 대표 논문 셋을 받아 둔다 (006).

    python tools/fetch_openalex.py icamg2026              # enrich/icamg2026.openalex.json
    python tools/fetch_openalex.py strati2026 --limit 100
    OPENALEX_API_KEY=… python tools/fetch_openalex.py …   # 무료 키 — 하루 한도가 10배

**받은 것은 다시 받지 않는다** — 파일에 있는 사람은 건너뛴다(`--refresh` 로 다시). 중간에 끊겨도
그때까지 받은 것은 남는다(사람마다 저장).

비용 (2026-10-08 응답 헤더로 확인): 저자 자동완성 `autocomplete/authors` 은 0, 저자의 논문 목록
`works?filter=author.id:` 은 1 크레딧. 키 없이 IP 당 하루 1,000 크레딧이라 사람 1,000 명이다.
남은 크레딧이 `--reserve` 아래로 내려가면 멈춘다.

**짝짓기.** 자동완성 후보 가운데 **이름이 같은 것**(악센트·하이픈·띄어쓰기를 지우고)만 보고,
후보마다 연구 주제(`authors/<id>` 의 topics — 비용 0)를 받아 점수를 매긴다:

    이 사람의 발표 제목·세션·키워드와 겹치는 주제어  ×2
    학회 전체 제목에 자주 나오는 낱말과 겹치는 주제어 ×1
    소속(hint)과 겹치는 낱말                        ×3

**5 점이 안 되면 짝을 짓지 않는다**(`match: null`). 처음에는 이름만 같으면 논문이 가장 많은
동명인을 골랐는데, ICAMG 다섯 명 가운데 셋이 의학·약학 연구자로 붙었다(구두 발표에 소속이
없다). 남의 논문을 그 사람 것처럼 보여 주느니 안 보여 주는 것이 낫다.

표준 라이브러리만 쓴다.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "web"))
from conference import people  # noqa: E402  (Django 없이 도는 모듈이다)

API = "https://api.openalex.org"
COMMON = {"with", "from", "their", "this", "that", "into", "over", "under", "between", "during",
          "based", "using", "study", "studies", "case", "new", "evidence", "insight", "insights",
          "implication", "implications", "analysis", "approach", "record", "records", "role",
          "change", "changes", "past", "late", "early", "high", "low", "since", "across", "toward",
          "towards", "through", "effect", "effects", "control", "controls", "processes", "process",
          "research", "sciences", "science", "system", "systems", "data", "model", "models"}
STOP = {"university", "of", "the", "and", "department", "dept", "school", "college", "institute",
        "national", "faculty", "center", "centre", "laboratory", "lab", "key", "state", "sciences",
        "science", "research", "for", "in", "at", "de", "da", "academy", "earth", "geology",
        "geological", "marine", "ocean", "china", "korea", "japan", "usa", "republic"}


def get(path, params, key=None):
    if key:
        params = {**params, "api_key": key}
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "confoinfo (+https://github.com/koprifossillab/confoinfo)"}),
                    timeout=12) as r:
                remaining = r.headers.get("X-RateLimit-Remaining")
                return json.load(r), int(remaining) if remaining and remaining.isdigit() else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit(f"한도에 걸렸다 (429) — 받은 데까지는 저장했다. 내일 이어서 돌린다")
            if attempt == 5:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            # 이 서버에서 바깥 연결이 자주 끊긴다 — 짧게 기다리고 여러 번 (처음엔 30초 × 4번이라
            # 사람 하나에 20초씩 걸렸다)
            if attempt == 5:
                raise
        time.sleep(1 + attempt)


def words(s):
    """소속 비교용 낱말."""
    return {w for w in re.findall(r"[a-z]{3,}", (s or "").lower()) if w not in STOP}


def topic_words(s):
    """주제 비교용 낱말 — 4자 이상, 흔한 낱말을 빼고, **앞 여섯 글자**로 줄인다.

    paleoclimatology·paleoceanographic → paleoc, Antarctica·Antarctic → antarc, sediments → sedime.
    소속용 STOP(geology·marine·ocean …)은 여기서 안 뺀다 — 처음에 같이 뺐더니 핵심 주제어가
    지워져 극지연구소의 Kyu-Cheul Yoo 가 짝을 못 찾았다.
    """
    return {w[:6] for w in re.findall(r"[a-z]{4,}", (s or "").lower()) if w not in COMMON}


MIN_SCORE = 5     # 4 점짜리가 딱정벌레 연구자였다 (ICAMG Young Kyu Park)


def match(name, affiliation, context, domain, key=None):
    """이름이 같은 후보 가운데 주제·소속 점수가 가장 높은 것. 모자라면 None."""
    data, _ = get("/autocomplete/authors", {"q": name}, key)
    same = [c for c in data.get("results", []) if people.norm(c["display_name"]) == people.norm(name)][:6]
    mine = words(affiliation)
    best, best_score, best_by = None, 0, ""
    for c in same:
        aid = c["id"].rsplit("/", 1)[-1]
        detail, _ = get(f"/authors/{aid}", {"select": "id,topics"}, key)          # 비용 0
        tw, fields = set(), set()
        for t in (detail.get("topics") or [])[:10]:
            w = topic_words(t["display_name"]) | topic_words(t["subfield"]["display_name"]) \
                | topic_words(t["field"]["display_name"])
            tw |= w
            if w & (context | domain):
                fields.add(t["field"]["display_name"])      # 이 학회와 맞는 주제가 든 분야
        aff = len(mine & words(c.get("hint")))
        score = 2 * len(context & tw) + len(domain & tw) + 3 * aff
        if score > best_score or (score == best_score and best and
                                  (c.get("works_count") or 0) > best["works_count"]):
            best, best_score, best_by = ({**_slim(c), "fields": sorted(fields)}, score,
                                         "affiliation" if aff else "topic")
        time.sleep(0.05)
    if not best or best_score < MIN_SCORE:
        return None
    return {**best, "by": best_by, "score": best_score}


def _slim(c):
    return {"id": c["id"].rsplit("/", 1)[-1], "name": c["display_name"], "hint": c.get("hint") or "",
            "works_count": c.get("works_count") or 0, "cited_by_count": c.get("cited_by_count") or 0}


def top_works(author_id, relevant, fields, key=None, n=3, pool=15):
    """많이 인용된 논문 pool 편을 받아, 이 학회의 주제와 겹치는 것 가운데 n 편.

    **OpenAlex 의 저자 한 명에 동명이인의 논문이 섞여 있다** — 해양지질학자 Kyung Eun Lee 의
    대표 논문에 의학 논문이 끼었다. 주된 주제의 분야가 그 사람의 "학회와 맞는 분야"(fields)에
들고 제목·주제가 이 학회 낱말과 겹치는 것만 남긴다 — 낱말만 보았더니 "fault" 가 겹쳐
컴퓨터 공학 논문(fault-recovery)이 들어왔다.
    한 요청이라 비용은 n 편만 받는 것과 같다(1 크레딧).
    """
    data, remaining = get("/works", {
        "filter": f"author.id:{author_id}", "sort": "cited_by_count:desc", "per-page": pool,
        "select": "id,display_name,publication_year,cited_by_count,doi,primary_location,primary_topic"},
        key)
    out = []
    for w in data.get("results", []):
        pt = w.get("primary_topic") or {}
        text = " ".join([w.get("display_name") or "", pt.get("display_name") or "",
                         (pt.get("subfield") or {}).get("display_name") or ""])
        field = (pt.get("field") or {}).get("display_name")
        if (fields and field not in fields) or not topic_words(text) & relevant:
            continue
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        out.append({"title": w.get("display_name") or "", "year": w.get("publication_year"),
                    "venue": src, "cited": w.get("cited_by_count") or 0,
                    "url": w.get("doi") or w["id"]})
        if len(out) == n:
            break
    return out, remaining


def conference_people(slug):
    """{people.key: {name, affiliation, context:set}} 와 학회 전체의 주제어(domain).

    context 는 그 사람이 나오는 발표들의 제목·세션 제목·키워드에서 뽑은 낱말이다.
    """
    data = json.loads((REPO / "conferences" / f"{slug}.json").read_text(encoding="utf-8"))
    abstracts = {a["key"]: a for a in data.get("abstracts") or []}
    sessions = {s["code"]: s.get("title", "") for s in data.get("sessions") or []}
    seen = {}
    linked = set()

    def add(found, text):
        ctx = topic_words(text)
        for p in found:
            k = people.key(p["name"], p["affiliation"])
            seen.setdefault(k, {**p, "context": set()})["context"] |= ctx

    for t in data.get("talks") or []:
        a = abstracts.get(t.get("abstract"))
        text = " ".join([t.get("title", ""), sessions.get(t.get("session"), ""),
                         " ".join((a or {}).get("keywords") or [])])
        if a:
            linked.add(a["key"])
            add(people.pick(a.get("authors"), a.get("affiliations")), text)
        else:
            add(people.pick([], [], t.get("speaker", ""), t.get("kind", "talk")), text)
    for k, a in abstracts.items():            # 프로그램에 없는 초록 (포스터 · 미편성)
        if k not in linked:
            text = " ".join([a.get("title", ""), sessions.get(a.get("session"), ""),
                             " ".join(a.get("keywords") or [])])
            add(people.pick(a.get("authors"), a.get("affiliations")), text)

    # 학회 전체 제목에서 자주 나오는 낱말 100개 — 이 학회가 무슨 분야인가
    freq = {}
    for t in data.get("talks") or []:
        for w in topic_words(t.get("title", "")):
            freq[w] = freq.get(w, 0) + 1
    domain = {w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:100]}
    return seen, domain


def main():
    ap = argparse.ArgumentParser(description="저자의 대표 논문을 OpenAlex 에서 미리 받는다")
    ap.add_argument("slug")
    ap.add_argument("--limit", type=int, default=0, help="이번에 받을 사람 수 (0 = 전부)")
    ap.add_argument("--reserve", type=int, default=30, help="남은 크레딧이 이 아래면 멈춘다")
    ap.add_argument("--refresh", action="store_true", help="받아 둔 사람도 다시")
    a = ap.parse_args()
    key = os.environ.get("OPENALEX_API_KEY") or None

    out_path = REPO / "enrich" / f"{a.slug}.openalex.json"
    out_path.parent.mkdir(exist_ok=True)
    store = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    store.setdefault("source", "OpenAlex (api.openalex.org) — tools/fetch_openalex.py")
    cache = store.setdefault("people", {})

    found, domain = conference_people(a.slug)
    todo = [(k, p) for k, p in found.items() if a.refresh or k not in cache]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{a.slug}: 받을 사람 {len(todo)} (받아 둔 사람 {len(cache)})")

    def save():
        store["fetched"] = dt.date.today().isoformat()
        out_path.write_text(json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")

    def one(item):
        k, p = item
        try:
            m = match(p["name"], p["affiliation"], p["context"], domain, key)
            works, remaining = (top_works(m["id"], p["context"] | domain, set(m["fields"]), key)
                                if m else ([], None))
        except Exception as e:                # 끊긴 사람은 다음에 다시 — 저장하지 않는다
            print(f"  ! {p['name']}: {e}", flush=True)
            return k, None, None
        if m and not works:
            m = None          # 주제가 맞는 논문이 하나도 없으면 다른 사람이라고 본다
        return k, {"name": p["name"], "affiliation": p["affiliation"], "match": m, "works": works}, remaining

    # 넷이 함께 — 사람 하나가 요청 서너 개라 초당 10 요청을 넘지 않는다
    from concurrent.futures import ThreadPoolExecutor
    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k, entry, remaining in pool.map(one, todo):
            if entry is None:
                continue
            cache[k] = entry
            done += 1
            if done % 20 == 0:
                save()
                print(f"  {done}/{len(todo)} · 남은 크레딧 {remaining}", flush=True)
            if remaining is not None and remaining < a.reserve:
                save()
                raise SystemExit(f"남은 크레딧 {remaining} — 멈춘다. 받은 {done} 명은 저장했다")
    save()
    matched = sum(1 for v in cache.values() if v["match"])
    print(f"끝 — {out_path.relative_to(REPO)}: 사람 {len(cache)} · 짝 지은 사람 {matched}")


if __name__ == "__main__":
    main()
