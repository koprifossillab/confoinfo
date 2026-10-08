# 학회 자료 형식 `confoinfo/1`

학회 하나 = 파일 하나 = `conferences/<slug>.json`. **파일 이름과 `conference.slug` 가
같아야 한다**(시험이 본다). 이 파일이 정본이고 DB 는 그것을 읽은 사본이다 —
`python web/manage.py import_conference --all` 이 맞추고, `tools/build_site.sh` 는
구울 때마다 임시 DB 에 새로 읽는다.

`main` 에 밀면 CI 가 사이트를 다시 구워 GitHub Pages 에 올린다 — 자료만 고쳐도 된다.

검사만 할 때:

```bash
python web/manage.py import_conference --check conferences/<slug>.json
```

## 모양

```jsonc
{
  "format": "confoinfo/1",
  "conference": {
    "slug": "strati2026",              // 필수. 영소문자·숫자·하이픈 40자 — URL 이 된다
    "short_name": "STRATI 2026",       // 필수. 머리글·카드·캘린더 이름
    "name": "5th International Congress on Stratigraphy",   // 필수
    "start_date": "2026-06-28",        // YYYY-MM-DD. 첫 화면의 진행 중·다가올·지난 갈래
    "end_date": "2026-07-03",
    "timezone": "Asia/Shanghai",       // 필수. IANA 이름 — 프로그램의 시각은 전부 개최지 시각
    "language": "en",                  // 제목·초록의 언어(BCP 47). 비면 en — 브라우저가 번역을 제안할지 정한다
    "venue": "Suzhou, China",
    "url": "https://www.strati2026.org/",
    "color": "#0d3b66",                // 머리글 색. 비면 기본 남색
    "lunch_at": "12:30",               // 점심 시각. 비면 12:30 (아래 "휴식")
    "source": "어디서 받은 자료인가"
  },
  "rooms": [                           // 순서가 곧 프로그램 화면의 룸 탭 순서
    {"name": "International Room I", "short": "Int'l I", "floor": "7F"}
  ],
  "sessions": [                        // 순서가 곧 세션 목록의 순서
    {"code": "G1", "group": "General", "title": "…", "poster_count": 3,
     "conveners": "좌장 A, 좌장 B",    // 세션 목록·상세에 나온다
     "description": "소개 문단\n\n- 항목\n- 항목"}   // 상세에서 펼친다. 빈 줄 = 문단, 줄바꿈 = <br>
  ],
  "abstracts": [
    {
      "key": "1",                      // 필수. 이 파일 안에서 하나뿐
      "session": "G1",
      "page": 37,                      // 초록집 쪽수
      "title": "…",                    // 필수
      "text": "본문",
      "keywords": ["…"],
      "authors": [{"name": "…", "affiliations": [1, 2], "corresponding": false}],
      "affiliations": ["1 번 소속", "2 번 소속"]
    }
  ],
  "talks": [
    {
      "key": "12",                     // 필수. 이 파일 안에서 하나뿐
      "date": "2026-06-29",            // 필수
      "start": "14:35",                // 필수. HH:MM (개최지 시각)
      "end": "14:50",
      "room": "International Room I",  // rooms 의 name. 없으면(null) 전체 행사 — "Plenary" 탭
      "session": "G4",                 // sessions 의 code
      "title": "…",                    // 필수
      "code": "P12",                   // 학회가 붙인 발표 번호(포스터 보드 등). 제목 옆 테두리 표시
      "speaker": "발표자 (보통 제1저자)",
      "kind": "talk",                  // talk · plenary · keynote · poster · break · event
      "abstract": "57",                // abstracts 의 key
      "page": 9                        // 핸드북 쪽수
    }
  ]
}
```

## `key` 를 바꾸지 말 것

**브라우저의 북마크·메모는 발표의 DB pk 에 붙는다.** 다시 읽어 들일 때 loader 가
발표의 pk 를 `(학회 slug, key)` 에서 계산하므로, 제목·시간·룸을 고쳐도 북마크가 따라간다.
**slug 를 바꾸는 것도 그 학회의 북마크를 전부 끊는다.**
`key` 를 바꾸면 다른 발표가 되어 그 발표의 북마크가 사라진다. 순서를 끼워 넣을
일이 있으면 줄 번호 말고 고정된 식별자를 쓴다.

자료에서 빠진 행은 DB 에서도 지워진다. **파일을 통째로 지워도 DB 의 학회는 남는다** —
내릴 때는 `import_conference --remove <slug>`.

## 경고와 오류

| | 처리 |
|---|---|
| `rooms` 에 없는 룸을 발표가 씀 | 경고 — 끝에 덧붙인다 |
| `sessions` 에 없는 세션 | 경고 — 세션 없이 둔다 |
| `abstracts` 에 없는 초록 | **오류** |
| `key` 겹침 · 날짜/시각 꼴 · 모르는 `kind` · 시간대 이름 | **오류** — 그 파일은 안 읽는다 |
| `slug` 가 다른 화면의 경로(`search`·`plan`·`settings`·`static`) | **오류** |

## 휴식

같은 날·같은 룸에서 이어지는 두 일정 사이가 **10분 이상** 비면 휴식으로 낸다(표시
전용, 북마크 안 됨). 그 빈 시간이 `lunch_at` 을 덮거나, 40분 이상이면서 점심
시간대(`lunch_at` −1시간 ~ +2시간 30분) 안에 통째로 들면 "Lunch", 아니면 "Break".

자료에 휴식이 `kind: "break"` 로 이미 있으면 그것이 자리를 차지하므로 앞뒤로
휴식이 두 번 생기지 않는다. 이름은 `title` 을 그대로 쓴다.

## 만드는 길

| 원본 | 길 |
|---|---|
| 스프레드시트·학회 사이트의 표 | CSV 로 내보내 `tools/csv2conf.py` — 예시 `docs/examples/` |
| PDF 핸드북·초록집 | `sources/<slug>/` 에 파서를 두고 이 형식으로 내보낸다 — 예 `sources/strati2026/` |
| 학회 사이트의 HTML 표 | 받은 HTML 을 `sources/<slug>/raw/` 에 커밋하고 파서로 — 예 `sources/icamg2026/` |
| 학회 API·JSON | 그 학회 전용 변환기를 `sources/<slug>/` 에 |

```bash
python tools/csv2conf.py docs/examples/example-program.csv \
    --meta docs/examples/example-meta.json -o conferences/example2026.json
```

`docs/examples/` 의 것은 가상의 학회라 `conferences/` 에 넣지 않는다.
