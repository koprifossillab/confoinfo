"""
화면. strati2026 4972d35 `congress/views.py` 에서 왔다 — 학회 하나 아래로 넣고
(`/<slug>/…`), 학회를 고르는 첫 화면과 학회를 가로지르는 검색·내 계획을 더했다.

동기화·기기 연결·사진·운영 설정(`/api/sync/`·`/api/pair/*`·`/api/photos/*`·
`/manage/`)은 아직 안 옮겼다 — 2단계다 (P01 4절).
"""
import datetime as dt
from collections import defaultdict

from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from confoinfoweb.version import VERSION

from .models import Abstract, Conference, Session, Talk

ALARM_MIN = 5             # 캘린더 알림: 발표 N분 전
MIN_BREAK_MIN = 10        # 이보다 짧은 빈 시간은 휴식으로 보지 않는다
DEFAULT_TALK_MIN = 20     # 끝 시각이 없는 발표의 길이 (캘린더·내 계획의 칸 높이)
SEARCH_LIMIT = 200


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
        "title": t.title,
        "author": t.speaker,
        "kind": t.kind,
        "url": reverse("talk_detail", args=[conf.slug, t.id]),
    }


# ── 첫 화면: 학회 고르기 ─────────────────────────────────────────────────

def home(request):
    confs = list(Conference.objects.annotate(
        n_talks=Count("talks", filter=~Q(talks__kind="break"), distinct=True),
        n_sessions=Count("sessions", distinct=True),
        n_abstracts=Count("abstracts", distinct=True),
    ))
    groups = {"ongoing": [], "upcoming": [], "past": []}
    for c in confs:
        groups[c.status()].append(c)
    # 다가오는 것은 가까운 것부터, 지난 것은 최근 것부터
    far = dt.date.max
    groups["upcoming"].sort(key=lambda c: (c.start_date or far, c.slug))
    sections = [("ongoing", "Now", groups["ongoing"]),
                ("upcoming", "Upcoming", groups["upcoming"]),
                ("past", "Past", groups["past"])]
    return render(request, "conference/home.html",
                  {"sections": [s for s in sections if s[2]], "n_confs": len(confs)})


# ── 학회 하나 ────────────────────────────────────────────────────────────

def program(request, slug):
    """일자별 프로그램. ?day=YYYY-MM-DD"""
    conf = _conf(slug)
    days = _days(conf)
    ctx = {"conf": conf, "days": days}
    if not days:
        return render(request, "conference/program.html", ctx)
    day_param = request.GET.get("day")
    if day_param:
        sel = next((d for d in days if d.isoformat() == day_param), days[0])
    else:
        # 고른 날이 없으면 개최지의 오늘을, 일정에 없으면 첫째 날을
        today = conf.today()
        sel = today if today in days else days[0]
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

    ctx.update({"selected": sel, "columns": columns, "plenary": plenary})
    return render(request, "conference/program.html", ctx)


def talk_detail(request, slug, pk):
    conf = _conf(slug)
    t = get_object_or_404(conf.talks.select_related("session", "abstract", "room"), pk=pk)
    return render(request, "conference/talk_detail.html",
                  {"conf": conf, "talk": t, "abstract": t.abstract, "session": t.session,
                   "obj_title": t.title})


def abstract_detail(request, slug, pk):
    conf = _conf(slug)
    a = get_object_or_404(conf.abstracts.select_related("session"), pk=pk)
    talk = a.talks.select_related("room", "session").first()
    return render(request, "conference/talk_detail.html",
                  {"conf": conf, "talk": talk, "abstract": a, "session": a.session,
                   "obj_title": a.title})


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
    """발표(제목·발표자·세션)와 프로그램에 없는 초록(제목·저자·키워드)을 찾는다.

    학회를 주면 그 안에서, 안 주면 모든 학회에서.
    """
    conf = _conf(slug) if slug else None
    q = (request.GET.get("q") or "").strip()
    talks, abstracts = [], []
    if q:
        tq = Talk.objects.exclude(kind="break").filter(
            Q(title__icontains=q) | Q(speaker__icontains=q) |
            Q(abstract__search_text__icontains=q) |       # 공저자·키워드
            Q(session__title__icontains=q) | Q(session__code__iexact=q)).distinct()
        aq = Abstract.objects.filter(talks__isnull=True).filter(
            Q(title__icontains=q) | Q(search_text__icontains=q))
        if conf:
            tq, aq = tq.filter(conference=conf), aq.filter(conference=conf)
        talks = list(tq.select_related("session", "room", "conference")[:SEARCH_LIMIT])
        abstracts = list(aq.select_related("session", "conference")[:SEARCH_LIMIT])
    return render(request, "conference/search.html",
                  {"conf": conf, "q": q, "talks": talks, "abstracts": abstracts,
                   "limit": SEARCH_LIMIT})


def plan(request, slug=None):
    """내 계획. 북마크는 localStorage 에 있어 JS 가 /api/talks/ 로 그린다.

    학회를 주면 그 학회의 것만, 안 주면 모든 학회의 북마크를 날짜순으로.
    """
    conf = _conf(slug) if slug else None
    return render(request, "conference/plan.html", {"conf": conf})


def settings_page(request):
    """표시 설정·이 기기의 자료 지우기. 값은 localStorage 에 있다."""
    return render(request, "conference/settings.html", {})


# ── API ──────────────────────────────────────────────────────────────────

def api_talks(request):
    """?ids=1,2,3 의 발표와, 그 발표로 이어지는 휴식(같은 날·같은 룸)."""
    want = {int(x) for x in (request.GET.get("ids") or "").split(",") if x.strip().isdigit()}
    sel = list(Talk.objects.filter(pk__in=want)
               .select_related("session", "room", "conference"))
    data = [_talk_payload(t) for t in sel]

    # 휴식은 그날 그 룸의 일정 전체에서 끌어낸다. 내 북마크만으로는 빈 시간이
    # 휴식인지 그냥 안 고른 발표인지 모른다.
    keys = {(t.conference_id, t.date, t.room_id) for t in sel if t.room_id}
    starts = {(t.conference_id, t.date, t.room_id, _hm(t.start)) for t in sel if t.room_id}
    grouped = defaultdict(list)
    if keys:
        q = Q()
        for c, d, r in keys:
            q |= Q(conference_id=c, date=d, room_id=r)
        for t in Talk.objects.filter(q).select_related("conference", "room"):
            grouped[(t.conference_id, t.date, t.room_id)].append(t)
    breaks = []
    for (c, d, r), ts in grouped.items():
        conf, room = ts[0].conference, ts[0].room
        for b in derive_breaks(ts, conf.lunch_at):
            end = _hm(b["end"])
            if (c, d, r, end) not in starts:
                continue   # 북마크한 발표로 이어지는 휴식만
            breaks.append({"conf": conf.slug, "date": d.isoformat(), "room": room.name,
                           "start": _hm(b["start"]), "end": end, "label": b["label"]})
    resp = JsonResponse({"talks": data, "breaks": breaks})
    # 자료는 배포 때만 바뀐다 → 판 쿼리(?v=)로 무효화하므로 길게 캐시해도 된다
    resp["Cache-Control"] = "public, max-age=86400"
    return resp


def _ics_escape(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;") \
        .replace(",", "\\,").replace("\n", "\\n")


def _ics_utc(date, t, tz):
    local = dt.datetime.combine(date, t, tzinfo=tz)
    return local.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def calendar_ics(request):
    """북마크한 발표를 폰 캘린더에 넣는다(.ics). 일정마다 N분 전 알림."""
    ids = [int(x) for x in request.GET.get("ids", "").split(",") if x.strip().isdigit()]
    talks = (Talk.objects.filter(id__in=ids).exclude(kind="break")
             .select_related("session", "room", "conference").order_by("date", "start"))
    confs = {t.conference.short_name for t in talks}
    calname = confs.pop() if len(confs) == 1 else "confoinfo"
    stamp = timezone.now().astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//confoinfo//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{_ics_escape(calname)}"]
    for t in talks:
        tz = t.conference.tz
        end_t = t.end or (dt.datetime.combine(dt.date.min, t.start)
                          + dt.timedelta(minutes=DEFAULT_TALK_MIN)).time()
        loc = ""
        if t.room:
            loc = t.room.name + (f" ({t.room.floor})" if t.room.floor else "")
        desc = " · ".join(p for p in [t.conference.short_name,
                                       t.session.code if t.session else "", t.speaker] if p)
        lines += [
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
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    resp = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="confoinfo.ics"'
    return resp


def healthz(request):
    """smoke.sh 가 본다 — 판이 갈렸는가, 자료가 있는가(빈 DB 를 물고도 200 은 나온다)."""
    return JsonResponse({
        "status": "ok",
        "version": VERSION,
        "conferences": Conference.objects.count(),
        "talks": Talk.objects.count(),
    })
