#!/usr/bin/env python3
"""학회 자료를 원본과 대조하기 전에 기계로 볼 것을 본다 — 반입 스킬(`.claude/skills/import-conference`)의 점검 단계.

    python tools/check_conf.py conferences/<slug>.json            # 요약 + 의심 행
    python tools/check_conf.py conferences/<slug>.json --sample 10 # 원본과 눈으로 대조할 표본
    python tools/check_conf.py conferences/<slug>.json --old <커밋>  # 다시 반입할 때 — 사라진 key(끊기는 북마크)

`import_conference --check` 는 형식이 맞는지를 본다. 이것은 **내용이 그럴듯한지**를 본다 — 같은 룸에서
시각이 겹치는 발표, 번호가 빈 포스터, 너무 짧거나 긴 제목, 발표자 없는 발표, 날짜가 학회 기간 밖인 것.
의심 행이 곧 오류는 아니다(협약식은 발표자가 없다). 하나씩 원본과 맞춰 보고 넘긴다.
"""
import argparse
import collections
import json
import random
import re
import subprocess
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def summary(d):
    c, T = d["conference"], d["talks"]
    kinds = collections.Counter(t.get("kind", "talk") for t in T)
    print(f"{c['slug']} · {c['short_name']} · {c.get('start_date')}~{c.get('end_date')} · {c.get('timezone')}")
    print(f"  룸 {len(d.get('rooms', []))} · 세션 {len(d.get('sessions', []))} · 초록 {len(d.get('abstracts', []))} · "
          f"발표 {len(T)} {dict(kinds)}")
    if len(c["short_name"]) > (13 if re.search(r"[가-힣]", c["short_name"]) else 18):
        print(f"  ? short_name 이 길다 — 머리글에서 두 줄로 넘어간다: {c['short_name']!r}")
    by = collections.defaultdict(list)
    for t in T:
        by[t["date"]].append(t)
    for day in sorted(by):
        rooms = collections.Counter(t.get("room") or "(전체)" for t in by[day])
        print(f"  {day}: {len(by[day])} — " + " · ".join(f"{r} {n}" for r, n in rooms.items()))


def hm(s):
    """`8:50` 과 `08:50` 을 같게 — 문자열로 비교하면 `8:50` 이 `10:00` 보다 크다."""
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def suspects(d):
    c, T = d["conference"], d["talks"]
    out = []
    lo, hi = c.get("start_date"), c.get("end_date") or c.get("start_date")
    abstracts = {a["key"]: a for a in d.get("abstracts", [])}
    by = collections.defaultdict(list)
    for t in T:
        if t.get("kind") not in ("break", "poster") and t.get("room"):
            by[(t["date"], t["room"])].append(t)
        if lo and not (lo <= t["date"] <= hi):
            out.append(("기간 밖", t))
        title = t.get("title", "")
        if (len(title) < 6 and t.get("kind", "talk") in ("talk", "poster")) or len(title) > 300:
            out.append(("제목 길이", t))
        if re.search(r"좌장|사회:|Chair:|\bp\.\s*\d+|\d{1,2}:\d{2}", title):
            out.append(("제목에 다른 줄이 섞임", t))
        if t.get("kind", "talk") in ("talk", "poster") and not t.get("speaker"):
            out.append(("발표자 없음", t))
        a = abstracts.get(t.get("abstract"))
        if a and any(len(x["name"]) > 40 for x in a.get("authors", [])):
            out.append(("저자 이름이 길다(쉼표가 안 갈림?)", t))
    for (day, room), ts in by.items():
        ts.sort(key=lambda t: hm(t["start"]))
        for a, b in zip(ts, ts[1:]):
            if a.get("end") and hm(a["end"]) > hm(b["start"]):
                out.append((f"시각 겹침 ← {a['key']} 끝 {a['end']}", b))
    codes = collections.defaultdict(list)
    for t in T:
        m = re.fullmatch(r"([A-Za-z-]*?)(\d+)", t.get("code") or "")
        if m:
            codes[m[1]].append(int(m[2]))
    for prefix, ns in codes.items():
        gaps = sorted(set(range(min(ns), max(ns) + 1)) - set(ns))
        dup = [n for n, k in collections.Counter(ns).items() if k > 1]
        if gaps:
            print(f"  ? 번호 {prefix}: 빠진 것 {gaps[:20]}{' …' if len(gaps) > 20 else ''}")
        if dup:
            print(f"  ? 번호 {prefix}: 겹친 것 {dup[:20]}")
    sess_codes = {s["code"] for s in d.get("sessions", [])}
    used = {t.get("session") for t in T} | {a.get("session") for a in d.get("abstracts", [])}
    for s in sorted(sess_codes - used):
        print(f"  ? 세션 {s}: 발표·초록이 하나도 없다")
    return out


def sample(d, n, seed):
    abstracts = {a["key"]: a for a in d.get("abstracts", [])}
    pool = [t for t in d["talks"] if t.get("kind", "talk") in ("talk", "poster")]
    random.seed(seed)
    for t in random.sample(pool, min(n, len(pool))):
        a = abstracts.get(t.get("abstract"), {})
        names = ", ".join(x["name"] + ("*" if x.get("corresponding") else "") for x in a.get("authors", []))
        print(f"\n{t['key']} · {t['date']} {t['start']}–{t.get('end', '')} · {t.get('room')} · {t.get('session')}"
              f"{' · p' + str(t['page']) if t.get('page') else ''}")
        print(f"  {t['title']}")
        print(f"  {names or t.get('speaker', '')}")


def lost_keys(path, old_rev):
    rel = Path(path).resolve().relative_to(Path.cwd().resolve())
    try:
        old = json.loads(subprocess.run(["git", "show", f"{old_rev}:{rel}"], check=True,
                                        capture_output=True, text=True).stdout)
    except subprocess.CalledProcessError:
        print(f"  {old_rev} 에 {rel} 이 없다 — 처음 넣는 학회")
        return
    new = load(path)
    ok, nk = {t["key"]: t for t in old["talks"]}, {t["key"] for t in new["talks"]}
    gone = [k for k in ok if k not in nk]
    print(f"  옛 발표 {len(ok)} → 새 {len(nk)} · 사라진 key {len(gone)} (그 북마크가 끊긴다) · 새 key {len(nk - set(ok))}")
    for k in gone[:30]:
        print(f"    - {k}  {ok[k]['title'][:60]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--old", help="비교할 옛 판의 git 커밋 (다시 반입할 때)")
    a = ap.parse_args()
    d = load(a.path)
    summary(d)
    rows = suspects(d)
    for why, t in rows[:80]:
        print(f"  ? {why}: {t['key']} · {t['date']} {t['start']} {t.get('room')} · {t.get('title', '')[:60]!r}")
    if len(rows) > 80:
        print(f"  … 의심 행 {len(rows) - 80}개 더")
    print(f"의심 행 {len(rows)}개" if rows else "의심 행 없음")
    if a.old:
        lost_keys(a.path, a.old)
    if a.sample:
        sample(d, a.sample, a.seed)


if __name__ == "__main__":
    sys.exit(main())
