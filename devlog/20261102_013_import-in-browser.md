# 013 학회를 브라우저에서 반입한다 — `/import/` · `/local/` · AI 지침

**날짜** 2026-11-02 · 계획은 [P02](20261102_P02_import-in-browser.md). 여기는 만들며 고른 것과 확인이다.
사용자가 "gsm-open repo 참고" 라고 해서 GSM 의 개인 레이어(wetherilli P08·118·130·131)를 본떴다.

## 지침 — 사용자의 AI 가 읽는다

- `docs/ai-guide.md`(영어) — 출력 규칙(JSON 하나, 지어내지 말 것, 번역하지 말 것, 개최지 시각), 칸마다 뜻, **key 를 행
  번호로 매기지 말 것**(북마크가 key 에 붙는다), 읽기를 멈추는 오류, 넘기기 전 점검 다섯, 최소 예시
- `docs/confoinfo-1.schema.json` — 칸의 꼴만 본다. 서로 가리키는 것(talk.room → rooms)과 겹침은 사이트가 본다
- 둘 다 사이트에 굽는다 — `format.txt`(`.md` 로 내면 Pages 가 HTML 로 바꿀 수 있다) · `confoinfo-1.schema.json`.
  반입 화면에 "Copy request" — 이 두 주소를 넣은 부탁 글을 복사해 AI 에게 프로그램과 함께 준다
- 시험이 지침의 최소 예시를 `loader.validate` 에 넣어 오류·경고가 없음을 본다 — AI 는 예시를 그대로 본뜬다

## 읽개 `local.js` 하나

GSM 의 `personal.js` 처럼 반입 화면·반입 학회 화면·내 계획·첫 화면이 같은 파일을 쓴다(`base.html` 이 싣는다).

- `validate` 는 `loader.validate` 를 옮긴 것이다. 메시지는 화면 문구라 영어. 하나 더 — **사이트에 이미 있는 slug 는
  받지 않는다**(같은 학회가 첫 화면에 둘 뜬다). 실제 세 학회 파일에서 JS·Python 모두 오류 0 · 경고 0 으로 같았다
- `stableId` — WebCrypto 의 SHA-1 로 `loader.stable_id` 와 같은 식. ICAMG 를 slug 만 바꿔 넣고, 같은 key 를
  `icamg2026` 으로 계산한 값이 구운 화면의 `data-id` 와 같음을 보았다. 그 학회가 나중에 정식으로 올라가도 북마크가 잇는다.
  WebCrypto 는 https·localhost 에서만 돈다 — Pages 는 https 다
- `prepare` — 룸 덧붙이기·모르는 세션 걷기(`loader.load` 와 같다)와 발표 pk 를 **저장할 때 한 번** 해 둔다. 화면은
  동기로 그린다. 받은 그대로(`orig`)도 같이 둔다 — 내려받기는 받은 파일을 돌려준다
- `deriveBreaks` — `views.derive_breaks` 를 옮겼다
- 저장은 IndexedDB(`confoinfo-local`), 열쇠는 slug. 같은 slug 를 다시 넣으면 "Replace" 로 바꾼다

## 반입 학회 화면 `/local/`

- 서버는 껍데기만 굽고 **구운 화면과 같은 HTML 꼴로 브라우저가 그린다** — CSS·북마크·메모·번역 링크·이름 한글 표시
  (011·012, `names.json` 에 있는 이름이면)가 그대로 돈다
- **쿼리로 가른다**(`?c=…&d=…`, `&talk=`, `&abstract=`, `&sessions=1`, `&session=`). 서버가 굽는 화면은 경로로만 가르지만
  (002) 이 화면은 파일 하나이고 브라우저 안에서만 그려진다. 링크마다 새로 읽으니 앞뒤 단추가 그대로다
- **프로그램 화면의 스크립트를 `program.js` 로 뺐다**(룸 탭·스와이프·플로팅·현재 시각 줄) — `program.html` 은 이제
  `CONFO.initProgram({…})` 한 줄이다. 두 화면이 따로 가지면 008 의 빨간 줄 같은 고침을 한쪽만 받는다
- 머리글·탭바는 base 의 학회 없는 꼴을 JS 가 채운다(학회 이름·색·LIVE·"on this device", 탭은 Program · Sessions ·
  My Plan · Conferences)
- 내 계획(전체)은 `talks.json` 에 `local.talksPayload()` 를 합친다. 학회 하나의 내 계획은 구운 학회뿐이라 손대지 않았다
- 첫 화면은 반입한 학회를 같은 카드에 `ON THIS DEVICE` 를 달아 같은 갈래(Now · Upcoming · Past)에 끼운다. 맨 아래
  "＋ Add a conference from a file". 설정 This device 에도 길을 두었다
- 서비스 워커 껍데기에 `/import/`·`/local/`·`local.js`·`program.js` 를 더했다 — 자료가 기기에 있으니 끊긴 곳에서도 열린다

## 반입 화면 `/import/`

GSM 118 의 관리 화면 꼴 — ① 파일 만들기(부탁 글 복사·지침·스키마) ② 넣기(고르기·끌어 놓기) → **저장 전에 읽은 것**
(학회·날짜·시간대, 날·룸·세션·발표·초록 수, 크기, 오류·경고 목록 30줄까지) → 오류가 없으면 "Save and open"
③ 이 기기의 것(열기·JSON 내려받기·지우기, 저장소 사용량, `navigator.storage.persist` 청하기, iOS 7일 안내).
지워도 북마크는 남는다 — 다시 넣으면 같은 key 의 발표에 다시 붙는다.

## 버린 것 · 미룬 것

- `#/…` 해시 길 — 한 페이지에서 화면을 갈아 끼우면 `program.js` 의 scroll·resize·setInterval 이 쌓인다. 쿼리 + 새로 읽기가 싸다
- CSV 반입 — 사용자의 AI 가 JSON 으로 옮기면 된다(P02)
- 반입 학회의 검색·.ics·대표 논문·미리 번역 — P02 "뒤로 미룬 것" 그대로

## 확인

시험 42개(`test_local` 다섯: 반입 화면에 구운 slug 목록, 껍데기, 지침·스키마 응답과 kind, local.js 의 예약 slug 가
`urls.RESERVED` 와 같음, 지침 예시가 검사 통과) · 개발 서버(Windows, 창이 가려진 브라우저):
틀린 파일 — 오류 넷(slug·시간대·날짜·없는 초록)과 경고 하나(없는 룸), 저장 단추 없음 · 구운 slug(`icamg2026`) — 막음 ·
ICAMG 를 `icamg-copy` 로 — 3일·5룸·36세션·193발표·184초록, 저장 → 프로그램이 오늘(11-02)로 열리고 LIVE·빨간 줄,
**룸 탭·룸마다 발표 수·휴식/점심이 구운 화면과 같다** · 북마크한 발표가 상세(★·메모·번역 링크)와 내 계획(전체)에 뜬다 ·
세션 목록 36 · 세션 1A 6발표 · 첫 화면 Now 에 ICAMG 2026 과 ICAMG copy(ON THIS DEVICE) · 사이트 굽기·링크 검사
