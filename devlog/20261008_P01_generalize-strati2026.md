# [계획] strati2026 을 어느 학회에나 쓰게 옮긴다

**작성일** 2026-10-08
**상태** 1단계까지 같은 날 끝냈다([001](20261008_001_stage1-generic-viewer.md)). 2단계부터는 5절의 물음이 정해진 뒤
**읽은 것** `jikhanjung/strati2026` 4972d35 (2026-06-30, v0.1.37) — `README.md`·`CLAUDE.md`·
`congress/` 전체·`static/`·`deploy/`·`devlog/` 제목 39개 · 환경은 `~/projects/ForGIA`(P01·`deploy/`)

---

## 0. 한 줄

strati2026 은 STRATI 2026 하나를 위한 앱이다 — 핸드북·초록집 PDF 를 파싱해 발표를
둘러보고, 북마크한 것을 시간·장소 타임테이블로 보여 준다. **화면과 북마크는 그대로
두고, 학회 하나에 묶인 자리를 걷어 내 여러 학회를 한 서버에서 연다.**

## 1. strati2026 에서 학회에 묶인 자리

| 자리 | strati2026 | 그래서 |
|---|---|---|
| 학회 | DB 전체가 STRATI 2026 하나 | `Conference` 를 맨 위에. 모든 행이 학회 아래 |
| 룸 순서·층 | `views.ROOM_ORDER` · `models.ROOM_FLOOR` · `short_room()` | `Room(order, short, floor)` — 자료의 순서가 탭 순서 |
| 날짜 | `"June 29"` 문자열 + `import_json.YEAR = 2026` | ISO 날짜. 화면이 표기를 정한다 |
| 시간대 | `Asia/Shanghai` 가 settings·views·템플릿 JS 셋에 | `Conference.timezone`. 현재 시각 줄·캘린더·"오늘" 이 학회마다 |
| 세션 정렬 | `int(code[1:])` — `G1` 꼴만 된다 | `Session.order` = 자료의 순서. 묶음은 `group` |
| 점심 | 12:30 을 덮는 빈 시간 | `Conference.lunch_at` (+ 001 의 시간대 규칙) |
| 자료 | `output/` 의 JSON 셋 — PDF 파서의 산출물 꼴 그대로 | **형식 하나**(`confoinfo/1`, `docs/data-format.md`). 학회마다 다른 원본은 변환기가 이 형식으로 |
| 적재 | 기본이 "다 지우고 다시" — pk 가 바뀐다 | 자료의 `key` 로 맞춘다. 배포 때 `--upsert` 를 쓰던 이유가 기본이 된다 |
| 북마크 키 | `strati_*` · 학회가 하나라 발표 pk 로 충분 | `confoinfo_*`. pk 가 학회를 가로질러 하나뿐이라 **학회마다 가를 필요가 없다** — 그래서 모든 학회의 내 계획이 공짜다 |

## 2. 무엇을 더하나

- **첫 화면 = 학회 고르기.** 진행 중(LIVE) · 다가올 · 지난 학회. 날짜는 개최지 시각으로
- **학회를 가로지르는 검색과 내 계획** (`/search/` · `/plan/`). 학회 안에서는 그 학회만
- **자료를 만드는 길 둘** — CSV(`tools/csv2conf.py`)와 학회별 변환기(`sources/<slug>/`).
  대부분의 학회는 PDF 보다 웹 페이지의 표나 스프레드시트로 프로그램을 낸다. 그것을
  손으로 CSV 로 옮기는 것이 가장 흔한 길이 될 것이다
- **명시적 휴식**(`kind: "break"`). strati2026 은 휴식을 빈 시간에서 끌어냈다 — 그것은
  남기되, 자료에 휴식이 적혀 있는 학회는 그대로 쓴다

## 3. 무엇을 얼마나 옮기나

| strati2026 | 판정 | 비고 |
|---|---|---|
| `scripts/parse_*.py` | 그대로 → `sources/strati2026/` | 경로(ROOT)만. 원본 PDF 는 없다 — 산출물(`output/`)을 함께 옮겼다 |
| `output/*.json` | 그대로 → `sources/strati2026/output/` | `to_confoinfo.py` 가 `conferences/strati2026.json` 으로 |
| `congress/models.py` | 손봄 | 학회 아래로. `SyncDevice`·`PairCode`·`SyncPhoto`·`ServerConfig` 는 2단계 |
| `congress/views.py` | 손봄 70% | 화면 넷·상세·API·캘린더는 학회 아래로. 동기화·사진·운영 설정은 2단계 |
| 템플릿 | 그대로 80% | 프로그램(룸 탭·현재 시각 줄·스와이프)·내 계획(겹침 격자·빈 시간 압축)은 손대지 않고 시간대와 경로만 |
| `static/app.js` | 손봄 | 북마크·메모만. 상태의 꼴(`{bm:{id:{v,ts}}}`)은 동기화를 붙일 때를 위해 그대로 |
| `static/style.css` | 그대로 | 동기화·사진 칸만 뺐다. 학회 색(`--navy`)을 자료에서 |
| `deploy/` | **안 옴** | 환경은 ForGIA 틀을 따른다(아래) |
| `admin/` · `/manage/` | 안 옴 · 2단계 | Django admin 은 안 쓴다(ForGIA 와 같다) |

**환경은 ForGIA(=DiaRUGA) 틀이다** — 사용자 방침. strati2026 의 Tailscale 포트 공개·
`honestjung/` 이미지 대신:

| | strati2026 | confoinfo |
|---|---|---|
| venv | `/home/jikhanjung/venv/strati2026` | `~/venv/confoinfo` · `workon ci` |
| 프로젝트 꼴 | `manage.py` 가 뿌리에 | `web/manage.py` · `web/confoinfoweb` · `web/conference` |
| 설정 | `STRATI_*` · `.env` 없음 | `CONFOINFO_*` · 뿌리의 `.env` 를 settings 가 읽는다 |
| 이미지 | `honestjung/strati2026` · `build.sh` 가 굽고 민다 | `koprifossillab/confoinfo` · **`v*` 태그 → CI** 가 시험 뒤 굽고 민다 |
| 배포 | `/srv/strati2026/deploy.sh` · `0.0.0.0:8010` | `/srv/confoinfo/bin/deploy.sh` · `127.0.0.1:8096` + nginx `/confoinfo/` · 유지보수 깃발 · smoke |
| 문서 | `CLAUDE.md` · `devlog/NNN` | `CLAUDE.md`(말 고르기) · `HANDOFF.md` · `TODOs.md` · `CHANGELOG.md` · `devlog/P`·`NNN` |

## 4. 단계

| 단계 | 무엇 | 상태 |
|---|---|---|
| **1** | 범용 모델·자료 형식·loader · 화면(첫 화면·프로그램·세션·검색·상세·내 계획·설정) · 캘린더 · STRATI 2026 이식 · CSV 도구 · 배포 틀 · 시험 | **끝**([001](20261008_001_stage1-generic-viewer.md)) |
| 2 | strati2026 의 기기 동기화(익명 토큰·6자리 연결 코드·기기 목록) · 메모 동기화 · 사진 · 운영 설정 화면. **여기서부터 DB 에 사람의 자료가 생긴다** — 백업(`backup_db.py`·시간별 cron·신선도 게이트)을 같이 | 5절 ① 이 정해진 뒤 |
| 3 | 학회를 둘째·셋째로 넣으며 형식이 모자란 곳을 채운다 — 포스터 세션(시간대만 있고 번호판), 다중 트랙 이름, 학회 안내(장소·지도·교통) | 실제 학회가 올 때 |
| 4 | 화면 문구 한국어 토글(국내 학회) · 오프라인(PWA) | |

## 5. 정할 것 (사용자)

1. **어디에 여는가.** strati2026 은 Tailscale 로 밖에서 붙었다(학회장에서 폰으로 쓴다).
   ForGIA 틀은 사내망 + VPN 이라 **학회장에 간 사람이 폰으로 못 연다.** 학회 앱의 쓰임과
   어긋난다. 공개 주소(도메인·TLS)를 둘지, 지금처럼 사내망에서 시작할지
2. **동기화를 옮기는가.** 공개로 열면 익명 토큰이라도 남의 기기 자료를 받는 서버가 된다.
   사내망이면 쓸 사람이 적다
3. **라이선스.** strati2026 에 LICENSE 가 없다. 이 저장소는 공개(public)다 — MIT 로 둘지
4. **넣을 학회.** 지금은 STRATI 2026 하나(지난 학회). 다음 학회가 무엇인지에 따라 3단계의 순서가 정해진다
