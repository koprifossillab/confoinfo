# CLAUDE.md

학회 프로그램을 한 눈에 보는 모바일 우선 웹 앱. 발표를 둘러보고 ☆ 북마크하면
**내 계획**(시간·장소 타임테이블)이 그려진다. **어느 학회든** 자료 파일 하나
(`conferences/<slug>.json`)를 넣으면 같은 화면으로 열린다.
STRATI 2026 하나를 위해 만든 `jikhanjung/strati2026` 을 범용으로 옮긴 것이다 —
무엇을 어떻게 옮겼는지는 [devlog/20261008_P01](devlog/20261008_P01_generalize-strati2026.md).
문서는 한국어로 쓴다 — 커밋 메시지, devlog, 주석 모두. **화면 문구는 영어다**
(국제 학회의 참가자가 쓴다).

## 자료의 층

```
학회      STRATI 2026                 Conference   ← slug 가 URL 이다 (/strati2026/)
 ├ 룸      International Room I        Room         ← 자료의 순서 = 탭 순서
 ├ 세션    G1 · S14                    Session      ← 묶음(group)으로 목록이 갈린다
 ├ 초록    초록집 한 편                 Abstract
 └ 발표    시간·장소가 잡힌 것          Talk         ← talk · plenary · keynote · poster · break · event
```

**정본은 `conferences/<slug>.json` 이다. DB 는 그 사본이다.** 형식은
[docs/data-format.md](docs/data-format.md). `import_conference` 가 자료의 `key` 로
행을 맞춰 **pk 를 지킨다** — 브라우저의 북마크·메모가 발표 pk 에 붙어 있기 때문이다.
**자료의 `key` 를 바꾸는 것은 그 발표의 북마크를 지우는 것이다.**

**학회마다 다른 것은 자료에 둔다, 코드에 두지 않는다.** strati2026 에서는 룸 순서·
층·날짜의 해·시간대·세션 코드 정렬이 코드에 박혀 있었다. 그것을 걷어 낸 것이 이
저장소의 전부다. 새 학회가 화면을 고쳐야 열린다면 그 차이를 자료 형식으로 올릴
수 있는지부터 본다.

**사람의 자료(북마크·메모)는 서버에 없다** — 브라우저 `localStorage` 에 있다
(`confoinfo_state`). 로그인도 없다. 2단계에서 strati2026 의 익명 기기 동기화를 옮기면
그때부터 DB 에 사람의 자료가 생긴다 — 백업 규약이 그때 붙는다(P01 4절).

## 이름

**`confoinfo` 하나다** — 저장소 `koprifossillab/confoinfo` 가 소문자라 그대로 따른다.
경로(`/srv/confoinfo`·`~/venv/confoinfo`)·URL(`/confoinfo/`)·DB(`confoinfo.db`)·
Docker Hub(`koprifossillab/confoinfo`)·`localStorage` 키(`confoinfo_*`) 전부.
환경변수는 `CONFOINFO_*`. 파이썬 패키지는 `confoinfoweb`(설정)·`conference`(앱).
화면에서는 학회 이름이 앞에 서고 confoinfo 는 머리글의 작은 글씨로만 나온다.

## 말을 고르는 규칙

DiaRUGA·ForGIA 의 규칙을 그대로 물려받는다. 지난 devlog 는 그때의 기록이라 안 고친다.

**한 낱말이 두 뜻을 겸하지 않게 한다.** `선다` 를 뜻마다 갈랐다(DiaRUGA 2026-08-12):

| 뜻 | 쓰는 말 |
|---|---|
| 돌다 말고 멈추다 | **멈춘다** |
| 임포트·설정이 성립하다 | **돈다** |
| 경고·띠가 나타나다 | **뜬다** |
| 행·개체가 만들어지다 | **생긴다** |
| 화면에서 자리를 잡다 | **놓인다** |
| 정렬·축의 기준이 되다 | **잡힌다** |
| 전제·비교가 유효하다 | **성립한다** |

**비유를 쓰지 않는다.** 이름과 문구가 실제와 어긋나면 둘 중 하나를 고친다.

**그 밖에 정해 둔 말** — 견주다 말고 **비교하다** · DB 의 것은 표 말고 **테이블**
(화면의 표는 "표") · 겹 말고 **레이어** · 순서대로 늘어놓는 것은 **정렬한다**.
이 저장소에서 더한 것: 학회 자료 파일은 **자료**(데이터·데이터셋 말고), 화면의
"My Plan" 은 문서에서 **내 계획**, 자료를 DB 로 넣는 것은 **읽어 들인다**.

## 시작하기 전에 읽을 것

**[HANDOFF.md](HANDOFF.md) 부터** — 지금 무엇이 있고 무엇이 막혀 있는지. 그 다음:

| 무엇을 하려는가 | 읽을 것 |
|---|---|
| 새 학회를 넣는다 | `docs/data-format.md` · CSV 면 `tools/csv2conf.py` · PDF 면 `sources/strati2026/` 을 본보기로 |
| 무엇을 옮겼고 무엇이 남았나 | `devlog/20261008_P01_generalize-strati2026.md` — 3절(자리마다) · 4절(단계) |
| 화면이 왜 그런가 | strati2026 저장소의 `devlog/` — 북마크·내 계획·현재 시각 줄의 근거가 거기 있다 |
| 스키마를 건드린다 | `web/conference/models.py` 머리말 · `loader.py` 머리말 |
| 앞으로 할 일 | `TODOs.md` |

**devlog 는 그때의 판단과 근거를 남기는 곳이다.** 계획은 `YYYYMMDD_PNN_주제.md`,
실제로 한 작업은 `YYYYMMDD_NNN_주제.md` 로 번호를 올려 가며 단계마다 끊어 적는다.
무엇을 했는지보다 **왜 그렇게 했고 무엇을 버렸는지**를 쓴다.

**strati2026 에서 온 파일은 머리에 출처 판을 적는다** (`strati2026 4972d35 …에서
왔다`). 저쪽이 고친 것을 따라갈 때 대조할 자리다.

배포·데이터 안전 규약은 `.guides/web/README.md` (형제 프로젝트들의 표준). **없으면
devdocs 클론이 안 걸린 것이다** — `../devdocs` 를 형제로 두고 `ln -s ../devdocs/guides
.guides`. 이 저장소에는 커밋하지 않는다(devdocs 는 private).

## 환경

```bash
workon ci               # ~/venv/confoinfo + ~/projects/confoinfo (저장소 안의 .venv 가 아니다)
python --version        # 3.12.3
pip install -r requirements.txt     # = -web(Django·whitenoise·gunicorn) + -dev(pymupdf·pdfplumber·playwright)
```

```bash
python web/manage.py migrate
python web/manage.py import_conference --all      # conferences/*.json → DB (pk 를 지키며)
python web/manage.py runserver                    # http://127.0.0.1:8000/
python web/manage.py test conference              # 시험 — 학회 자료 파일 검사도 여기 있다
```

DB 는 저장소 뿌리의 `confoinfo.db`(gitignore) — 학회 자료의 사본이라 지워도 된다.
위치를 바꾸려면 `.env`(`.env.template` 참고).

```
/srv/confoinfo/   db/  bin/  www/  backup/  docker-compose.yml  .env     ← 배포
```

## 배포

DiaRUGA·ForGIA 와 같은 틀이다. 같은 서버에 **8096** 으로 뜨고 nginx 의 `/confoinfo/`
서브경로가 받는다(사내 VPN 이 80 만 통과시킨다).

1. 판을 `web/confoinfoweb/version.py` · `CHANGELOG.md` 에 올리고 `main` 에 민다
2. `vX.Y.Z` 태그를 민다 → CI 가 시험을 돌리고 `koprifossillab/confoinfo:vX.Y.Z` 를 Docker Hub 에 올린다
3. 서버에서 `/srv/confoinfo/bin/deploy.sh vX.Y.Z` — 받고, 갈아 끼우고, health 게이트, smoke

**학회 자료가 이미지에 들어간다.** 자료만 고쳐도 판을 올린다 — 기동 때 entrypoint 가
`import_conference --all` 을 돈다. 배포 파일이 바뀌었으면 `deploy/host/sync_to_srv.sh`.

## 커밋

- 커밋 메시지는 한국어. **파일을 지정해 add** 한다(`git add -A` 금지 — 원본 PDF·DB 가 섞인다)
- 원격은 HTTPS(`https://github.com/koprifossillab/confoinfo.git`) — gh 의 `wetherilli` 로 민다
