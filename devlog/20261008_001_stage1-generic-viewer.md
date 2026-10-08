# 001 1단계 — 범용 모델·자료 형식·화면·배포 틀

**날짜** 2026-10-08 · 계획 [P01](20261008_P01_generalize-strati2026.md) 4절의 1단계

## 한 것

- `Conference` · `Room` · `Session` · `Abstract` · `Talk` (`web/conference/models.py`)
- 자료 형식 `confoinfo/1`(`docs/data-format.md`) · `loader.py`(검사·읽어 들이기) ·
  `import_conference`(`--all` · `--check` · `--remove`)
- 화면: 첫 화면(학회 고르기) · 프로그램 · 세션 목록·상세 · 발표·초록 상세(메모) ·
  검색(학회 안·전체) · 내 계획(학회 안·전체) · 설정 · `calendar.ics` · `api/talks/` · `/healthz`
- STRATI 2026 이식: `sources/strati2026/`(파서 둘 + 산출물) → `to_confoinfo.py` →
  `conferences/strati2026.json` — 룸 6 · 세션 30 · 초록 607 · 발표 457 (초록 연결 429)
- `tools/csv2conf.py` + `docs/examples/`(가상 학회 하나)
- 배포 틀: `deploy/Dockerfile` · `entrypoint-web.sh` · `srv/{docker-compose.yml,env.template}` ·
  `host/{deploy,smoke,sync_to_srv}.sh` · `nginx/confoinfo-subpath.conf` + 안내 페이지 둘 ·
  `.github/workflows/test.yml`
- 시험 27개 (`web/conference/tests/`)

## 판단

**자료의 `key` 로 맞춘다 — "다 지우고 다시" 를 버렸다.** strati2026 의 `import_json` 은
기본이 wipe 였고 배포 entrypoint 만 `--upsert` 를 썼다. wipe 하면 발표 pk 가 바뀌어
브라우저의 북마크가 다른 발표를 가리킨다 — 그 위험을 entrypoint 한 줄이 막고 있던
셈이다. 여기서는 loader 가 늘 key 로 맞추고 자료에서 빠진 행만 지운다. strati2026 의
`id` 를 `key` 로 옮겼으므로 같은 파서 산출물에서 같은 key 가 나온다.

**`--all` 은 파일이 없어진 학회를 지우지 않는다.** 파일 이름을 잘못 옮긴 한 번에 학회가
통째로 사라지고, 그 학회의 북마크가 전부 끊긴다. 내릴 때는 `--remove` 로 사람이 한다.

**세션 G18·S14 를 세션으로 세웠다.** strati2026 은 사이트 콤보박스에 없던 두 세션을
행으로 안 만들어, 그 세션의 초록이 세션 없이(`session=None`) 들어갔다. 초록집에는 있으니
제목만 빈 세션으로 둔다 — 화면이 "(title TBD)" 를 낸다.

**점심 규칙을 넓혔다.** strati2026 은 12:30 을 덮는 빈 시간만 점심이었다. `lunch_at` 으로
뺐더니 시험의 가상 학회(점심 12:00, 빈 시간 12:10~13:00)에서 점심을 놓쳤다. 처음에는
"가운데가 점심 시각에서 90분 안" 으로 했는데 09:40~11:50 같은 오전 공백이 점심이 됐다.
**점심 시간대(−60 ~ +150분) 안에 통째로 든 40분 이상 빈 시간**으로 정했다.
STRATI 2026 의 휴식 54건(Break 42 · Lunch 12)은 옛 규칙과 하나도 안 다르다 — 바꾸기 전후를 비교했다.

**검색이 공저자·키워드를 본다.** strati2026 은 제목·제1저자·세션 제목만 봤다. 초록의
저자 이름은 JSON 칸에 있는데, SQLite 의 JSON 칸은 비ASCII 를 `\uXXXX` 로 적어 두어
`Montañez` 가 `icontains` 에 안 걸린다. 그래서 `Abstract.search_text`(저자·키워드를
이은 평문)를 loader 가 채운다. 프로그램에 없는 초록(포스터·미편성)도 따로 찾는다.

**"오늘 일정 없음" 띠를 학회 기간에만 띄운다.** strati2026 은 학회가 하나뿐이라 그 띠가
학회 기간 밖에서 뜨는 것이 맞았다. 여러 학회를 둘러보는 앱에서는 지난 학회를 열 때마다
뜨는 띠가 된다.

**STATIC_URL 에 서브경로를 직접 붙였다.** 상대경로(`"static/"`)로 두면 Django 가
SCRIPT_NAME 을 붙여 주는데, **처음 읽힌 값을 캐시한다.** gunicorn 에서는 whitenoise 가
요청이 오기 전에 읽어 접두 없는 `/static/` 이 굳었고, `/confoinfo/` 아래에서 CSS·JS 가
404 였다. 이미지를 띄워 보고서야 보였다 — 개발 서버(DEBUG)에서는 안 난다.
ForGIA 는 정적 파일이 없어(템플릿 인라인) 이 자리를 안 밟는다.

**whitenoise 는 이미지에서만 낀다.** collectstatic 은 Dockerfile 이 빌드 때 돌리고
(`CONFOINFO_STATIC_MANIFEST=1`), 개발·시험은 Django 기본 저장소를 쓴다. Manifest
저장소는 manifest 가 없으면 템플릿을 못 그린다.

## 버린 것

- **동기화·사진·운영 설정**(strati2026 028~039) — 2단계. 공개 여부(P01 5절 ①)가 정해져야
  한다. 그때 붙이기 쉽게 브라우저 상태의 꼴(`{bm:{id:{v,ts}}, notes:{…}}`)은 그대로 뒀다
- **Django admin** — ForGIA 와 같이 안 쓴다. 자료는 파일이 정본이라 화면에서 고칠 것이 없다
- **학회별 `ROOM_FLOOR` 같은 상수를 변환기 밖에 두는 것** — `sources/strati2026/to_confoinfo.py`
  에만 있다. 뷰어는 STRATI 를 모른다
- **`schema.sql`·`handbook.json`(위원회·기조연사·답사)** — strati2026 의 남은 할 일이었다.
  범용 형식에 넣을지는 3단계에서 실제 학회 둘째를 보고

## 확인

- 시험 27개 통과 — loader(검사·pk 유지·정리·학회 둘·모르는 룸/세션), 화면 전부, 개최지 시각
  기준 "오늘", 휴식 판정, API 의 휴식 고르기, ICS 의 UTC 변환, 서브경로 링크·STATIC_URL,
  저장소의 자료 파일 전부 검사
- 헤드리스 크로미움(playwright 1.49.1, 390×844): 첫 화면 · 프로그램 북마크 · 가상 학회의 룸 탭·
  명시적 휴식·점심 · 상세의 메모 · 전체 내 계획(학회 둘이 날짜·학회로 갈림) · 콘솔 오류 없음
- 이미지(156 MB)를 `-u 1000:1000` 서브경로 설정으로 띄워 migrate → 자료 읽기 → `/healthz` →
  해시 붙은 CSS·JS 200 → 재기동 때 "(새로)" 없이 다시 맞추는 것까지

## 남은 것

`HANDOFF.md` 0절(저장소 쓰기 권한 · `/srv/confoinfo` · nginx · Docker Hub 시크릿)과 `TODOs.md`.
