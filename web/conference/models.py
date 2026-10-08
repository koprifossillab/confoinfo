"""
학회 · 룸 · 세션 · 초록 · 발표.

strati2026 의 `congress/models.py`(Session·Abstract·Talk)를 학회 하나 아래로 넣었다
(P01 2절). 그쪽은 DB 전체가 STRATI 2026 하나였고 학회마다 다른 것 — 룸 순서와
층(`ROOM_FLOOR`), 날짜의 해(`YEAR`), 시간대(`Asia/Shanghai`), 세션 코드 정렬
(`int(code[1:])`) — 이 코드에 박혀 있었다. 여기서는 전부 자료의 것이다.

**정본은 `conferences/<slug>.json` 이다.** DB 는 그것을 읽은 사본이고
`import_conference` 가 맞춘다. 각 행의 `key` 가 자료 파일 안의 식별자이고, **발표·초록의
pk 는 (학회 slug, key) 에서 계산한다**(`loader.stable_id`) — 브라우저의 북마크·메모가
발표 pk 로 붙어 있고, 구운 사이트는 빌드마다 빈 DB 에서 새로 읽기 때문이다.
"""
import datetime as dt
from zoneinfo import ZoneInfo

from django.db import models


class Conference(models.Model):
    slug = models.SlugField(max_length=40, unique=True)     # URL · 자료 파일 이름
    short_name = models.CharField(max_length=60)            # "STRATI 2026"
    name = models.CharField(max_length=300)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=60, default="UTC")   # IANA 이름 — 개최지 시각
    # 자료(제목·초록)의 언어. <html lang> 이 되어 브라우저가 번역을 제안할지 정한다 (004)
    language = models.CharField(max_length=20, default="en")
    venue = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True)
    color = models.CharField(max_length=20, blank=True)     # 머리글 색. 비면 기본
    # 이 시각을 덮는 빈 시간을 "Lunch" 라 부른다 (strati2026 의 12:30 이 기본값)
    lunch_at = models.TimeField(default=dt.time(12, 30))
    source = models.CharField(max_length=300, blank=True)   # 자료가 어디서 왔나
    imported = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "slug"]

    def __str__(self):
        return self.short_name

    @property
    def tz(self):
        return ZoneInfo(self.timezone)

    def today(self, now=None):
        """개최지 시각으로 오늘."""
        from django.utils import timezone
        return (now or timezone.now()).astimezone(self.tz).date()

    def status(self, today=None):
        """ongoing · upcoming · past. 날짜가 없으면 upcoming 으로 본다."""
        today = today or self.today()
        start = self.start_date
        end = self.end_date or start
        if start is None:
            return "upcoming"
        if today < start:
            return "upcoming"
        if today > end:
            return "past"
        return "ongoing"


class Room(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=120)
    short = models.CharField(max_length=40, blank=True)     # 룸 탭에 들어가는 짧은 이름
    floor = models.CharField(max_length=40, blank=True)
    order = models.IntegerField(default=0)                  # 자료 파일의 순서 = 탭 순서

    class Meta:
        ordering = ["conference", "order", "name"]
        constraints = [models.UniqueConstraint(fields=["conference", "name"],
                                               name="room_unique_name")]

    def __str__(self):
        return self.name

    @property
    def label(self):
        return self.short or self.name


class Session(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name="sessions")
    code = models.CharField(max_length=20)                  # "G1" · "S14" · "T3-2"
    group = models.CharField(max_length=80, blank=True)     # 세션 목록의 묶음 (General · Special …)
    title = models.CharField(max_length=500, blank=True)
    conveners = models.CharField(max_length=500, blank=True)   # 좌장 — "A, B"
    description = models.TextField(blank=True)                 # 세션 소개 (문단은 빈 줄로)
    poster_count = models.IntegerField(default=0)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["conference", "order", "code"]
        constraints = [models.UniqueConstraint(fields=["conference", "code"],
                                               name="session_unique_code")]

    def __str__(self):
        return f"{self.code}. {self.title}"


class Abstract(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name="abstracts")
    key = models.CharField(max_length=40)
    session = models.ForeignKey(Session, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="abstracts")
    page = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=800)
    text = models.TextField(blank=True)
    keywords = models.JSONField(default=list)               # ["kw1", ...]
    authors = models.JSONField(default=list)                # [{name, affiliations:[1,2], corresponding}]
    affiliations = models.JSONField(default=list)           # ["1 의 소속", "2 의 소속", ...]
    # 저자 이름과 키워드를 이은 것 — 검색용. JSON 칸은 비ASCII 를 \uXXXX 로 적어 두어
    # `authors__icontains="Montañez"` 가 안 걸린다. loader 가 채운다
    search_text = models.TextField(blank=True)

    class Meta:
        ordering = ["conference", "id"]
        constraints = [models.UniqueConstraint(fields=["conference", "key"],
                                               name="abstract_unique_key")]

    def __str__(self):
        return self.title

    @property
    def author_line(self):
        return ", ".join(a.get("name", "") for a in self.authors)

    @property
    def corresponding(self):
        return [a["name"] for a in self.authors if a.get("corresponding")]


class Talk(models.Model):
    """프로그램에 시간과 자리가 잡힌 것 하나. 발표 · 기조 · 휴식 · 행사."""
    KINDS = ["talk", "plenary", "keynote", "poster", "break", "event"]
    # 북마크할 수 없는 것 — 프로그램에 자리만 차지한다
    UNBOOKMARKABLE = {"break"}

    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name="talks")
    key = models.CharField(max_length=40)
    date = models.DateField()
    start = models.TimeField()
    end = models.TimeField(null=True, blank=True)
    # 룸이 없으면 전체 행사(기조·개회 등)다. 프로그램 화면에서 따로 탭이 생긴다
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="talks")
    session = models.ForeignKey(Session, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="talks")
    # 학회가 붙인 발표 번호 — 포스터 보드 번호("P12")·구두 번호("O-3"). 없으면 비운다
    code = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=800)
    speaker = models.CharField(max_length=300, blank=True)
    kind = models.CharField(max_length=16, default="talk")
    abstract = models.ForeignKey(Abstract, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="talks")
    page = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["conference", "date", "start", "room__order"]
        constraints = [models.UniqueConstraint(fields=["conference", "key"],
                                               name="talk_unique_key")]

    def __str__(self):
        return f"[{self.date} {self.start:%H:%M}] {self.title}"

    @property
    def bookmarkable(self):
        return self.kind not in self.UNBOOKMARKABLE
