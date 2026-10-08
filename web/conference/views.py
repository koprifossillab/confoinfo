"""
화면. strati2026 4972d35 `congress/views.py` 에서 왔다 — 학회 하나 아래로 넣고
(`/<slug>/…`), 학회를 고르는 첫 화면과 학회를 가로지르는 검색·내 계획을 더했다.

**모든 응답이 요청과 무관하다 — 쿼리 문자열도, 요청 시각도 안 본다** (002).
`build_site` 가 이 화면들을 파일로 구워 GitHub Pages 에 올리기 때문이다. 그래서
날짜는 경로(`/<slug>/day/<날짜>/`)로 가르고, "오늘" 을 고르는 일·검색·내 계획·여러
발표의 캘린더는 브라우저(JS)가 정적 JSON 을 받아 한다. 여기에 `request.GET` 이나
`timezone.now()` 를 들이면 구운 사이트에서만 틀린다.
"""
import datetime as dt
import json
import re
from collections import defaultdict

from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from . import changelog
from .models import Conference, Session, Talk

ALARM_MIN = 5             # 캘린더 알림: 발표 N분 전
MIN_BREAK_MIN = 10        # 이보다 짧은 빈 시간은 휴식으로 보지 않는다
DEFAULT_TALK_MIN = 20     # 끝 시각이 없는 발표의 길이 (캘린더·내 계획의 칸 높이)


# ── 휴식 ─────────────────────────────────────────────────────────────────

def _minutes(t):
    return t.hour * 60 + t.minute


LUNCH_MIN = 40            # 이보다 짧으면 점심이 아니다
# 점심 시간대 = 점심 시각 −60분 ~ +150분. 빈 시간이 통째로 이 안에 있어야 한다
LUNCH_BEFORE, LUNCH_AFTER = 60, 150


def _break_label(start, end, lunch_at):
    """빈 시간 → "Lunch" · "Break".

    strati2026 은 12:30 을 덮는 빈 시간만 점심이었다. 학회마다 점심 시각이 달라
    `lunch_at` 으로 뺐는데, 그 시각을 조금 지나 시작하는 점심(12:00 기준에 12:10~13:00)
    을 놓친다. 그래서 점심 시간대 안에 통째로 든 긴 빈 시간도 점심으로 본다 —
    "가운데가 가까우면" 으로 했더니 09:40~11:50 같은 오전 공백이 점심이 됐다.
    """
    s, e, l = _minutes(start), _minutes(end), _minutes(lunch_at)
    if s <= l <= e:
        return "Lunch"
    if e - s >= LUNCH_MIN and s >= l - LUNCH_BEFORE and e <= l + LUNCH_AFTER:
        return "Lunch"
    return "Break"


def derive_breaks(items, lunch_at):
    """같은 (날짜·룸)에서 이어지는 두 일정 사이의 빈 시간 → 휴식(표시 전용).

    자료에 휴식이 `kind: break` 로 이미 있으면 그것도 자리를 차지하므로, 그 앞뒤로는
    빈 시간이 안 생긴다 — 같은 휴식이 두 번 뜨지 않는다.
    """
    ts = sorted([t for t in items if t.start and t.end], key=lambda t: t.start)
    out = []
    for a, b in zip(ts, ts[1:]):
        if b.start > a.end and _minutes(b.start) - _minutes(a.end) >= MIN_BREAK_MIN:
            out.append({"start": a.end, "end": b.start,
                        "label": _break_label(a.end, b.start, lunch_at)})
    return out


# ── 공통 ─────────────────────────────────────────────────────────────────

def _conf(slug):
    return get_object_or_404(Conference, slug=slug)


def _days(conf):
    return list(conf.talks.order_by("date").values_list("date", flat=True).distinct())


def _hm(t):
    return t.strftime("%H:%M") if t else ""


def _talk_payload(t):
    conf = t.conference
    return {
        "id": t.id,
        "conf": conf.slug,
        "conf_name": conf.short_name,
        "tz": conf.timezone,
        "date": t.date.isoformat(),
        "room": t.room.name if t.room else "",
        "floor": t.room.floor if t.room else "",
        "session": t.session.code if t.session else "",
        "start": _hm(t.start),
        "end": _hm(t.end),
        "code": t.code,
        "title": t.title,
        "author": t.speaker,
        "kind": t.kind,
        "url": reverse("talk_detail", args=[conf.slug, t.id]),
    }


def _json(data):
    # 한글·악센트를 \uXXXX 로 풀지 않는다 — 파일이 작아지고 사람이 읽을 수 있다
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False, "separators": (",", ":")})


def _confs(slug):
    return [_conf(slug)] if slug else list(Conference.objects.all())


# ── 첫 화면: 학회 고르기 ─────────────────────────────────────────────────

def home(request):
    """학회 카드를 시작일 순으로. 진행 중·다가올·지난 갈래는 JS 가 오늘을 보고 가른다."""
    confs = Conference.objects.annotate(
        n_talks=Count("talks", filter=~Q(talks__kind="break"), distinct=True),
        n_sessions=Count("sessions", distinct=True),
        n_abstracts=Count("abstracts", distinct=True),
    ).order_by("start_date", "slug")
    return render(request, "conference/home.html", {"confs": confs})


# ── 학회 하나 ────────────────────────────────────────────────────────────

def program(request, slug, day=None):
    """일자별 프로그램. `/<slug>/` 는 첫째 날이고, 학회 기간이면 JS 가 오늘로 넘긴다."""
    conf = _conf(slug)
    days = _days(conf)
    ctx = {"conf": conf, "days": days, "is_root": day is None}
    if not days:
        if day is not None:
            raise Http404
        return render(request, "conference/program.html", ctx)
    if day is None:
        sel = days[0]
    else:
        try:
            sel = dt.date.fromisoformat(day)
        except ValueError:
            raise Http404
        if sel not in days:
            raise Http404
    talks = list(conf.talks.filter(date=sel).select_related("session", "abstract", "room"))

    rooms = sorted({t.room for t in talks if t.room}, key=lambda r: (r.order, r.name))
    by_room = {r.pk: [] for r in rooms}
    plenary = []
    for t in talks:
        (by_room[t.room_id] if t.room_id else plenary).append(t)
    columns = []
    for r in rooms:
        # 자료에 적힌 휴식(kind=break)은 끌어낸 휴식과 같은 모양으로 낸다
        items = [("break", {"start": t.start, "end": t.end or t.start, "label": t.title})
                 if t.kind == "break" else ("talk", t) for t in by_room[r.pk]]
        items += [("break", b) for b in derive_breaks(by_room[r.pk], conf.lunch_at)]
        items.sort(key=lambda it: it[1].start if it[0] == "talk" else it[1]["start"])
        columns.append((r, items))

    day_urls = {d.isoformat(): reverse("program_day", args=[slug, d.isoformat()]) for d in days}
    ctx.update({"selected": sel, "columns": columns, "plenary": plenary,
                "day_urls": json.dumps(day_urls)})
    return render(request, "conference/program.html", ctx)


_HONORIFIC = re.compile(r"^(Prof\.?|Professor|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+", re.I)


def scholar_people(talk, abstract):
    """Google Scholar 링크를 달 사람 — 제1저자와 교신저자 (005).

    Scholar 는 API 가 없고 자동으로 긁는 것을 막아 목록을 가져오지 않는다. 이름으로 찾는
    링크만 단다. 동명이인을 가를 수 있게 그 사람의 소속을 곁에 적는다.
    [{name, roles: ["1st author", "corresponding"], affiliation}]
    """
    out = []

    def add(name, role, affiliation=""):
        name = _HONORIFIC.sub("", re.sub(r"\s*\(.*?\)", "", name or "")).strip(" ,;*")
        if not name:
            return
        hit = next((p for p in out if p["name"].lower() == name.lower()), None)
        if hit:
            if role not in hit["roles"]:
                hit["roles"].append(role)
            hit["affiliation"] = hit["affiliation"] or affiliation
        else:
            out.append({"name": name, "roles": [role], "affiliation": affiliation})

    def affil_of(author):
        refs = author.get("affiliations") or []
        affs = abstract.affiliations or []
        return "; ".join(affs[r - 1] for r in refs if isinstance(r, int) and 0 < r <= len(affs))

    if abstract and abstract.authors:
        first = abstract.authors[0]
        add(first.get("name"), "1st author", affil_of(first))
        for a in abstract.authors:
            if a.get("corresponding"):
                add(a.get("name"), "corresponding", affil_of(a))
    elif talk and talk.kind in ("talk", "plenary", "keynote", "poster"):
        add(talk.speaker, "speaker")
    return out


def talk_detail(request, slug, pk):
    conf = _conf(slug)
    t = get_object_or_404(conf.talks.select_related("session", "abstract", "room"), pk=pk)
    return render(request, "conference/talk_detail.html",
                  {"conf": conf, "talk": t, "abstract": t.abstract, "session": t.session,
                   "obj_title": t.title, "people": scholar_people(t, t.abstract)})


def abstract_detail(request, slug, pk):
    conf = _conf(slug)
    a = get_object_or_404(conf.abstracts.select_related("session"), pk=pk)
    talk = a.talks.select_related("room", "session").first()
    return render(request, "conference/talk_detail.html",
                  {"conf": conf, "talk": talk, "abstract": a, "session": a.session,
                   "obj_title": a.title, "people": scholar_people(talk, a)})


def sessions(request, slug):
    conf = _conf(slug)
    items = conf.sessions.annotate(
        n_talks=Count("talks", filter=~Q(talks__kind="break"), distinct=True),
        n_abs=Count("abstracts", distinct=True),
    )
    groups = []
    for s in items:
        if not groups or groups[-1][0] != s.group:
            groups.append((s.group, []))
        groups[-1][1].append(s)
    return render(request, "conference/sessions.html", {"conf": conf, "groups": groups})


def session_detail(request, slug, code):
    conf = _conf(slug)
    s = get_object_or_404(Session, conference=conf, code=code)
    talks = list(s.talks.exclude(kind="break")
                 .select_related("abstract", "session", "room", "conference"))
    linked = {t.abstract_id for t in talks if t.abstract_id}
    extra = [a for a in s.abstracts.select_related("conference") if a.id not in linked]   # 구두 미편성 · 포스터
    return render(request, "conference/session_detail.html",
                  {"conf": conf, "session": s, "talks": talks, "extra": extra})


def search(request, slug=None):
    """검색 화면. 찾는 것은 JS 가 search.json 을 받아 브라우저에서 한다."""
    conf = _conf(slug) if slug else None
    return render(request, "conference/search.html", {"conf": conf})


def plan(request, slug=None):
    """내 계획. 북마크는 localStorage 에 있어 JS 가 talks.json 으로 그린다.

    학회를 주면 그 학회의 것만, 안 주면 모든 학회의 북마크를 날짜순으로.
    """
    conf = _conf(slug) if slug else None
    return render(request, "conference/plan.html", {"conf": conf})


def settings_page(request):
    """기본 학회·모양·번역 언어 설정, 판 이력, 이 기기의 자료 지우기. 설정값은 localStorage 에 있다."""
    try:
        notes = changelog.parse((settings.PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    except OSError:
        notes = []
    return render(request, "conference/settings.html",
                  {"confs": Conference.objects.order_by("-start_date", "slug"), "notes": notes})


# ── 정적 JSON (build_site 가 파일로 굽는다) ──────────────────────────────

def talks_json(request, slug=None):
    """발표 전부와 휴식 전부 — 내 계획이 북마크한 것만 골라 그린다.

    strati2026 의 `/api/talks/?ids=` 는 북마크한 것만 받았다. 정적 사이트에는 쿼리가
    없어 통째로 낸다(STRATI 2026 이 gzip 전 100 KB 남짓). 학회가 많아져 무거우면
    학회별 파일만 받게 바꾼다 — 전체 내 계획이 학회 목록을 보고 필요한 것만 받으면 된다.
    """
    talks, breaks = [], []
    for conf in _confs(slug):
        ts = list(conf.talks.select_related("session", "room", "conference"))
        talks += [_talk_payload(t) for t in ts if t.bookmarkable]
        grouped = defaultdict(list)
        for t in ts:
            if t.room_id:
                grouped[(t.date, t.room)].append(t)
        for (d, room), items in grouped.items():
            found = [{"start": t.start, "end": t.end, "label": t.title}
                     for t in items if t.kind == "break" and t.end]
            found += derive_breaks(items, conf.lunch_at)
            breaks += [{"conf": conf.slug, "date": d.isoformat(), "room": room.name,
                        "start": _hm(b["start"]), "end": _hm(b["end"]), "label": b["label"]}
                       for b in found]
    return _json({"talks": talks, "breaks": breaks})


def search_json(request, slug=None):
    """검색 색인. `x` 는 제목 밖에서 찾을 글 — 발표자·공저자·키워드·세션 제목.

    초록 본문은 안 넣는다(STRATI 2026 만으로 1 MB 가 넘는다). 프로그램에 자리가 없는
    초록(포스터·미편성)은 `talks` 와 따로 `abstracts` 에.
    """
    talks, abstracts = [], []
    for conf in _confs(slug):
        for t in conf.talks.exclude(kind="break").select_related("session", "room", "abstract"):
            extra = [t.speaker]
            if t.abstract:
                extra.append(t.abstract.search_text)
            if t.session:
                extra += [t.session.code, t.session.title]
            p = _talk_payload(t)
            p["x"] = " ".join(e for e in extra if e)
            talks.append(p)
        for a in conf.abstracts.filter(talks__isnull=True).select_related("session"):
            abstracts.append({
                "id": a.id, "conf": conf.slug, "conf_name": conf.short_name,
                "title": a.title, "authors": a.author_line,
                "session": a.session.code if a.session else "",
                "url": reverse("abstract_detail", args=[conf.slug, a.id]),
                "x": " ".join(e for e in [a.search_text, a.session.title if a.session else ""] if e),
            })
    return _json({"talks": talks, "abstracts": abstracts})


def _ics_escape(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;") \
        .replace(",", "\\,").replace("\n", "\\n")


def _ics_utc(date, t, tz):
    local = dt.datetime.combine(date, t, tzinfo=tz)
    return local.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def talk_ics(request, slug, pk):
    """발표 하나를 폰 캘린더에(.ics). N분 전 알림. 여러 발표는 내 계획의 JS 가 만든다."""
    conf = _conf(slug)
    t = get_object_or_404(conf.talks.exclude(kind="break").select_related("session", "room"), pk=pk)
    tz = conf.tz
    end_t = t.end or (dt.datetime.combine(dt.date.min, t.start)
                      + dt.timedelta(minutes=DEFAULT_TALK_MIN)).time()
    loc = ""
    if t.room:
        loc = t.room.name + (f" ({t.room.floor})" if t.room.floor else "")
    desc = " · ".join(p for p in [conf.short_name, t.session.code if t.session else "",
                                   t.speaker] if p)
    # DTSTAMP 는 발표 시작 시각으로 둔다 — 구울 때마다 파일이 바뀌지 않게
    stamp = _ics_utc(t.date, t.start, tz)
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//confoinfo//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{_ics_escape(conf.short_name)}",
        "BEGIN:VEVENT",
        f"UID:talk-{t.id}@confoinfo",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{_ics_utc(t.date, t.start, tz)}",
        f"DTEND:{_ics_utc(t.date, end_t, tz)}",
        f"SUMMARY:{_ics_escape(t.title)}",
        f"LOCATION:{_ics_escape(loc)}",
        f"DESCRIPTION:{_ics_escape(desc)}",
        "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Reminder",
        f"TRIGGER:-PT{ALARM_MIN}M", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    resp = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/calendar; charset=utf-8")
    return resp


def not_found(request):
    """GitHub Pages 의 404.html 로 굽는다."""
    return render(request, "conference/404.html", {}, status=404)
