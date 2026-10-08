/* confoinfo — 북마크·메모 (localStorage).
   strati2026 4972d35 static/app.js 에서 왔다. 서버 동기화·기기 연결·사진은 2단계라
   여기서 뺐다 — 그래도 상태는 그쪽과 같은 꼴({bm:{id:{v,ts}}, notes:{…}})로 둔다.
   동기화가 항목마다 ts 큰 쪽을 고르므로(last-write-wins) 붙일 때 옮길 것이 없다.

   북마크는 발표 pk 로 붙는다. pk 는 학회를 가로질러 하나뿐이라 학회마다 따로 둘
   필요가 없고, 내 계획(/plan/)이 모든 학회의 북마크를 한 번에 그린다. */
(function () {
  const SKEY = "confoinfo_state";   // {bm:{id:{v,ts}}, notes:{id:{v,ts}}}
  const CKEY = "confoinfo_cfg";     // 표시 설정
  const CFG_DEFAULT = { breaks: true };
  const ROOT = (window.CONFO && window.CONFO.root) || "/";

  function getCfg() {
    try { return Object.assign({}, CFG_DEFAULT, JSON.parse(localStorage.getItem(CKEY) || "{}")); }
    catch (e) { return Object.assign({}, CFG_DEFAULT); }
  }
  function setCfg(patch) {
    const c = Object.assign(getCfg(), patch);
    localStorage.setItem(CKEY, JSON.stringify(c));
    return c;
  }
  function resetLocal() {
    [SKEY, CKEY].forEach(k => localStorage.removeItem(k));
  }

  function nowTs() { return Date.now(); }
  function loadState() {
    try {
      const s = JSON.parse(localStorage.getItem(SKEY));
      if (s && s.bm && s.notes) return s;
    } catch (e) { /* 아래로 */ }
    return { bm: {}, notes: {} };
  }
  let STATE = loadState();
  function saveState() { localStorage.setItem(SKEY, JSON.stringify(STATE)); }

  function getBM() {
    return Object.keys(STATE.bm).filter(id => STATE.bm[id] && STATE.bm[id].v).map(Number);
  }
  function isBM(id) { const e = STATE.bm[id]; return !!(e && e.v); }
  function setBMv(id, on) { STATE.bm[id] = { v: on, ts: nowTs() }; saveState(); }
  function toggle(id) { const on = !isBM(id); setBMv(id, on); return on; }
  // 없으면 북마크를 더한다. 메모를 남기면 자동 북마크.
  function ensureBM(id) {
    if (isBM(id)) return false;
    setBMv(id, true);
    document.querySelectorAll('.bm[data-id="' + id + '"]').forEach(paint);
    document.dispatchEvent(new CustomEvent("bm:change", { detail: { id } }));
    return true;
  }

  function getNote(id) { const e = STATE.notes[id]; return (e && e.v) || ""; }
  function hasNote(id) { const e = STATE.notes[id]; return !!(e && e.v); }
  function setNote(id, text) {
    text = (text || "").trim();
    STATE.notes[id] = { v: text, ts: nowTs() };   // "" = 지움 (동기화의 tombstone 자리)
    saveState();
    if (text) ensureBM(id);
  }

  // 개최지 시각의 오늘 날짜·분. 기기 시간대와 무관하다.
  function zoneNow(tz) {
    const f = new Intl.DateTimeFormat("en-CA", {
      timeZone: tz || "UTC", hour12: false,
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    }).formatToParts(new Date());
    const g = t => f.find(p => p.type === t).value;
    // 일부 브라우저가 자정을 "24" 로 낸다
    return { date: `${g("year")}-${g("month")}-${g("day")}`,
             min: (+g("hour") % 24) * 60 + +g("minute") };
  }
  function parseMin(s) {                     // "HH:MM" → 분
    const m = /^(\d{1,2}):(\d{2})$/.exec(s || "");
    return m ? +m[1] * 60 + +m[2] : null;
  }

  // 대소문자·악센트를 지운 글 — 검색에서 "montanez" 가 "Montañez" 에 걸리게
  function fold(s) {
    return (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  // ── 캘린더(.ics) ─────────────────────────────────────────────────────
  // 정적 사이트라 여러 발표를 묶은 .ics 는 여기서 만든다. 발표 하나짜리는
  // 서버가 구운 talk.ics 가 있다 (views.talk_ics 와 같은 꼴).
  const ALARM_MIN = 5, DEFAULT_TALK_MIN = 20;
  function tzOffsetMin(utcMs, tz) {          // 그 순간 tz 의 UTC 오프셋(분)
    const f = new Intl.DateTimeFormat("en-CA", { timeZone: tz, hour12: false,
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
      .formatToParts(new Date(utcMs));
    const g = t => +f.find(p => p.type === t).value;
    const asUtc = Date.UTC(g("year"), g("month") - 1, g("day"), g("hour") % 24, g("minute"));
    return (asUtc - utcMs) / 60000;
  }
  function zonedToUtc(date, hm, tz) {        // "2026-06-29", "14:35", "Asia/Shanghai" → Date
    const [y, mo, d] = date.split("-").map(Number), [h, mi] = hm.split(":").map(Number);
    const guess = Date.UTC(y, mo - 1, d, h, mi);
    let t = guess - tzOffsetMin(guess, tz) * 60000;
    t = guess - tzOffsetMin(t, tz) * 60000;  // 서머타임 경계에서 한 번 더
    return new Date(t);
  }
  function icsStamp(dt) { return dt.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); }
  function icsEsc(s) {
    return (s || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
  }
  function buildIcs(talks, calname) {
    const L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//confoinfo//EN", "CALSCALE:GREGORIAN",
               "METHOD:PUBLISH", "X-WR-CALNAME:" + icsEsc(calname || "confoinfo")];
    const stamp = icsStamp(new Date());
    talks.forEach(t => {
      const s = zonedToUtc(t.date, t.start, t.tz);
      const e = t.end && t.end > t.start ? zonedToUtc(t.date, t.end, t.tz)
                                         : new Date(s.getTime() + DEFAULT_TALK_MIN * 60000);
      const loc = t.room ? t.room + (t.floor ? ` (${t.floor})` : "") : "";
      L.push("BEGIN:VEVENT", `UID:talk-${t.id}@confoinfo`, "DTSTAMP:" + stamp,
             "DTSTART:" + icsStamp(s), "DTEND:" + icsStamp(e), "SUMMARY:" + icsEsc(t.title),
             "LOCATION:" + icsEsc(loc),
             "DESCRIPTION:" + icsEsc([t.conf_name, t.session, t.author].filter(Boolean).join(" · ")),
             "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Reminder",
             `TRIGGER:-PT${ALARM_MIN}M`, "END:VALARM", "END:VEVENT");
    });
    L.push("END:VCALENDAR");
    return L.join("\r\n") + "\r\n";
  }
  function downloadIcs(talks, calname) {
    const blob = new Blob([buildIcs(talks, calname)], { type: "text/calendar;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "confoinfo.ics";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  }

  // ── 화면 도우미 ──────────────────────────────────────────────────────
  function esc(s) {
    return (s || "").replace(/[&<>"']/g, c => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function paint(btn) {
    const on = isBM(parseInt(btn.dataset.id, 10));
    btn.textContent = on ? "★" : "☆";
    btn.classList.toggle("on", on);
  }
  function refresh() {
    document.querySelectorAll(".bm").forEach(paint);
    document.querySelectorAll(".talk[data-id]").forEach(el => {
      el.classList.toggle("has-note", hasNote(parseInt(el.dataset.id, 10)));
    });
  }

  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".bm");
    if (!btn) return;
    e.preventDefault();
    const id = parseInt(btn.dataset.id, 10);
    toggle(id);
    document.querySelectorAll('.bm[data-id="' + id + '"]').forEach(paint);
    document.dispatchEvent(new CustomEvent("bm:change", { detail: { id } }));
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.body.classList.toggle("hide-breaks", !getCfg().breaks);
    refresh();
  });

  window.CONFO = Object.assign(window.CONFO || {}, {
    root: ROOT,
    getBM, isBM, toggle, esc, refresh, getNote, hasNote, setNote,
    getCfg, setCfg, resetLocal, zoneNow, parseMin, fold, zonedToUtc, buildIcs, downloadIcs,
  });
})();
