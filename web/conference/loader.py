"""
학회 자료 파일(`confoinfo/1`) → DB. 형식은 `docs/data-format.md`.

    errors, warnings = validate(data)
    stats = load(data)          # validate 를 통과한 것만

**발표·초록의 pk 는 (학회 slug, key) 에서 계산한다** (`stable_id`, 003) — 빈 DB 에 어떤
순서로 읽어도 같은 pk 가 나온다. 행마다 자료 안의 `key`(룸은 이름, 세션은 코드)로 같은
것을 찾아 고치고, 자료에서 사라진 것만 지운다. strati2026 은
기본이 "전부 지우고 다시" 였는데, 그러면 발표 pk 가 바뀌어 브라우저에 남은
북마크가 엉뚱한 발표를 가리킨다. 그쪽도 그래서 배포 때는 `--upsert` 를 썼다.
"""
import datetime as dt
import hashlib
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction

from .urls import RESERVED
from .models import Abstract, Conference, Room, Session, Talk

FORMAT = "confoinfo/1"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")

CONF_FIELDS = ["short_name", "name", "start_date", "end_date", "timezone", "language",
               "venue", "url", "color", "lunch_at", "source"]


def _date(s):
    return dt.date.fromisoformat(s) if s else None


def _time(s):
    if not s:
        return None
    h, m = s.split(":")
    return dt.time(int(h), int(m))


def validate(data):
    """(오류, 경고). 오류가 하나라도 있으면 읽어 들이지 않는다."""
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["최상위가 객체가 아니다"], warnings
    if data.get("format") != FORMAT:
        errors.append(f"format 이 {FORMAT!r} 이 아니다: {data.get('format')!r}")

    conf = data.get("conference") or {}
    slug = conf.get("slug", "")
    if not SLUG_RE.match(slug or ""):
        errors.append(f"conference.slug 는 영소문자·숫자·하이픈 40자 이내: {slug!r}")
    elif slug in RESERVED:
        errors.append(f"conference.slug {slug!r} 는 다른 화면의 경로라 못 쓴다")
    for f in ("short_name", "name"):
        if not conf.get(f):
            errors.append(f"conference.{f} 가 비었다")
    try:
        ZoneInfo(conf.get("timezone") or "")
    except (ZoneInfoNotFoundError, ValueError):
        errors.append(f"conference.timezone 이 IANA 이름이 아니다: {conf.get('timezone')!r}")
    for f in ("start_date", "end_date"):
        try:
            _date(conf.get(f))
        except ValueError:
            errors.append(f"conference.{f} 가 YYYY-MM-DD 가 아니다: {conf.get(f)!r}")
    if conf.get("language") and not LANG_RE.match(conf["language"]):
        errors.append(f"conference.language 가 BCP 47 꼴(en · ko · zh-CN)이 아니다: {conf['language']!r}")
    if conf.get("lunch_at") and not TIME_RE.match(conf["lunch_at"]):
        errors.append(f"conference.lunch_at 이 HH:MM 이 아니다: {conf['lunch_at']!r}")

    def unique(items, field, what):
        seen = set()
        for i, it in enumerate(items):
            k = it.get(field)
            if not k:
                errors.append(f"{what}[{i}].{field} 가 비었다")
            elif k in seen:
                errors.append(f"{what} 의 {field} 가 겹친다: {k!r}")
            seen.add(k)
        return seen

    rooms = unique(data.get("rooms") or [], "name", "rooms")
    sessions = unique(data.get("sessions") or [], "code", "sessions")
    abstracts = unique(data.get("abstracts") or [], "key", "abstracts")
    for a in data.get("abstracts") or []:
        if not a.get("title"):
            errors.append(f"abstracts[{a.get('key')!r}].title 이 비었다")
        if a.get("session") and a["session"] not in sessions:
            warnings.append(f"초록 {a.get('key')!r} 의 세션 {a['session']!r} 이 sessions 에 없다 — 세션 없이 둔다")

    unique(data.get("talks") or [], "key", "talks")
    new_rooms = set()
    for t in data.get("talks") or []:
        k = t.get("key")
        try:
            _date(t.get("date")) or errors.append(f"발표 {k!r} 의 date 가 비었다")
        except ValueError:
            errors.append(f"발표 {k!r} 의 date 가 YYYY-MM-DD 가 아니다: {t.get('date')!r}")
        if not TIME_RE.match(t.get("start") or ""):
            errors.append(f"발표 {k!r} 의 start 가 HH:MM 이 아니다: {t.get('start')!r}")
        if t.get("end") and not TIME_RE.match(t["end"]):
            errors.append(f"발표 {k!r} 의 end 가 HH:MM 이 아니다: {t['end']!r}")
        if not t.get("title"):
            errors.append(f"발표 {k!r} 의 title 이 비었다")
        if t.get("kind", "talk") not in Talk.KINDS:
            errors.append(f"발표 {k!r} 의 kind 가 {Talk.KINDS} 중 하나가 아니다: {t.get('kind')!r}")
        if t.get("room") and t["room"] not in rooms:
            new_rooms.add(t["room"])
        if t.get("session") and t["session"] not in sessions:
            warnings.append(f"발표 {k!r} 의 세션 {t['session']!r} 이 sessions 에 없다 — 세션 없이 둔다")
        if t.get("abstract") and t["abstract"] not in abstracts:
            errors.append(f"발표 {k!r} 의 abstract {t['abstract']!r} 가 abstracts 에 없다")
    for r in sorted(new_rooms):
        warnings.append(f"룸 {r!r} 이 rooms 에 없다 — 끝에 덧붙인다")
    return errors, warnings


def stable_id(slug, key):
    """(학회 slug, 자료의 key) → 정해진 pk. 52비트라 JS 의 Number 로도 정확하다.

    **북마크는 발표 pk 에 붙는다.** 처음에는 DB 가 매기는 일련번호를 key 로 지켰는데, 구운
    사이트는 빌드마다 빈 DB 에 새로 읽어 pk 가 **읽는 순서**로 정해졌다 — 학회 하나가 앞에
    끼자 다른 학회의 pk 가 전부 밀렸다(003). 그래서 pk 를 자료에서 계산한다.
    """
    return int(hashlib.sha1(f"{slug}/{key}".encode()).hexdigest()[:13], 16)


def _sync(model, conference, items, lookup, defaults_of, pk_of=None):
    """lookup 칸으로 행을 맞추고 자료에 없는 행을 지운다. {lookup 값: 행} 을 돌려준다.

    pk_of 를 주면 그 pk 로 만든다. 예전 DB 에 다른 pk 로 있던 행은 지우고 다시 만든다.
    """
    existing = {getattr(o, lookup): o for o in model.objects.filter(conference=conference)}
    out = {}
    for i, it in enumerate(items):
        k = it[lookup]
        values = defaults_of(i, it)
        obj = existing.pop(k, None)
        want = pk_of(k) if pk_of else None
        if obj is not None and want is not None and obj.pk != want:
            obj.delete()
            obj = None
        if obj is None:
            extra = {"pk": want} if want is not None else {}
            obj = model.objects.create(conference=conference, **{lookup: k}, **values, **extra)
        else:
            changed = [f for f, v in values.items() if getattr(obj, f) != v]
            for f in changed:
                setattr(obj, f, values[f])
            if changed:
                obj.save(update_fields=changed)
        out[k] = obj
    stale = [o.pk for o in existing.values()]
    if stale:
        model.objects.filter(pk__in=stale).delete()
    return out, len(stale)


@transaction.atomic
def load(data):
    conf_in = data["conference"]
    values = {f: conf_in.get(f) for f in CONF_FIELDS if f in conf_in}
    for f in ("start_date", "end_date"):
        if f in values:
            values[f] = _date(values[f])
    if values.get("lunch_at"):
        values["lunch_at"] = _time(values["lunch_at"])
    else:
        values.pop("lunch_at", None)
    for f in ("venue", "url", "color", "source"):
        if f in values and values[f] is None:
            values[f] = ""
    conf, created = Conference.objects.update_or_create(slug=conf_in["slug"], defaults=values)

    rooms_in = list(data.get("rooms") or [])
    known = {r["name"] for r in rooms_in}
    for t in data.get("talks") or []:
        if t.get("room") and t["room"] not in known:
            rooms_in.append({"name": t["room"]})
            known.add(t["room"])
    rooms, rooms_gone = _sync(Room, conf, rooms_in, "name", lambda i, r: {
        "short": r.get("short") or "", "floor": r.get("floor") or "", "order": i})

    sessions, sessions_gone = _sync(Session, conf, data.get("sessions") or [], "code", lambda i, s: {
        "group": s.get("group") or "", "title": s.get("title") or "",
        "conveners": s.get("conveners") or "", "description": s.get("description") or "",
        "poster_count": s.get("poster_count") or 0, "order": i})

    def abstract_values(i, a):
        s = sessions.get(a.get("session"))
        return {"session_id": s.pk if s else None, "page": a.get("page"),
                "title": a["title"], "text": a.get("text") or "",
                "keywords": a.get("keywords") or [], "authors": a.get("authors") or [],
                "affiliations": a.get("affiliations") or [],
                "search_text": " · ".join(
                    [au.get("name", "") for au in a.get("authors") or []]
                    + list(a.get("keywords") or []))}
    abstracts, abstracts_gone = _sync(Abstract, conf, data.get("abstracts") or [], "key",
                                      abstract_values,
                                      pk_of=lambda k: stable_id(conf.slug, "abstract/" + k))

    def talk_values(i, t):
        r, s, a = rooms.get(t.get("room")), sessions.get(t.get("session")), abstracts.get(t.get("abstract"))
        return {"date": _date(t["date"]), "start": _time(t["start"]), "end": _time(t.get("end")),
                "room_id": r.pk if r else None, "session_id": s.pk if s else None,
                "code": t.get("code") or "",
                "title": t["title"], "speaker": t.get("speaker") or "",
                "kind": t.get("kind") or "talk", "abstract_id": a.pk if a else None,
                "page": t.get("page")}
    talks, talks_gone = _sync(Talk, conf, data.get("talks") or [], "key", talk_values,
                              pk_of=lambda k: stable_id(conf.slug, k))

    return {
        "slug": conf.slug, "created": created,
        "rooms": len(rooms), "sessions": len(sessions),
        "abstracts": len(abstracts), "talks": len(talks),
        "linked": sum(1 for t in talks.values() if t.abstract_id),
        "removed": rooms_gone + sessions_gone + abstracts_gone + talks_gone,
    }
