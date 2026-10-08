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
  // 모양 (005). 값이 목록에 없으면 기본값 — 옛 판이 남긴 값이나 손으로 고친 값을 거른다 (GSM readLook)
  const LOOKS = { theme: ["auto", "light", "dark"], font: ["sans", "serif", "system"] };
  function getLook(key) {
    const v = getCfg()[key];
    return LOOKS[key].includes(v) ? v : LOOKS[key][0];
  }
  const darkMq = window.matchMedia ? matchMedia("(prefers-color-scheme: dark)") : null;
  function applyLook() {
    const d = document.documentElement, t = getLook("theme");
    d.setAttribute("data-theme", t === "auto" ? (darkMq && darkMq.matches ? "dark" : "light") : t);
    const f = getLook("font");
    if (f === "sans") d.removeAttribute("data-font"); else d.setAttribute("data-font", f);
  }
  function setLook(key, value) { setCfg({ [key]: value }); applyLook(); }
  // "Auto" 이면 기기가 다크 모드를 바꾸는 대로 따라간다
  if (darkMq && darkMq.addEventListener) darkMq.addEventListener("change", applyLook);

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

  // ── 번역 (004) ───────────────────────────────────────────────────────
  // 서버가 없어 번역을 직접 하지 않는다. 글을 번역 사이트로 넘기는 링크만 만든다 —
  // 키도 비용도 없다. 긴 초록은 사이트의 글자 수 한도에 걸려 문단 단위로 나눈다.
  const LANGS = [["ko", "한국어"], ["ja", "日本語"], ["zh-CN", "中文(简体)"], ["zh-TW", "中文(繁體)"],
                 ["vi", "Tiếng Việt"], ["th", "ไทย"], ["id", "Bahasa Indonesia"], ["en", "English"],
                 ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"], ["ru", "Русский"]];
  // Papago 가 받는 언어 (Google 은 전부 받는다)
  const PAPAGO = new Set(["ko", "ja", "zh-CN", "zh-TW", "vi", "th", "id", "en", "es", "fr", "de", "ru"]);
  const SERVICES = [
    { name: "Papago", limit: 3000, ok: l => PAPAGO.has(l),
      url: (t, l) => "https://papago.naver.com/?sk=auto&tk=" + l + "&st=" + encodeURIComponent(t) },
    { name: "Google", limit: 4500, ok: () => true,
      url: (t, l) => "https://translate.google.com/?sl=auto&tl=" + l + "&op=translate&text=" + encodeURIComponent(t) },
  ];
  function xlateLang() {
    const saved = getCfg().lang;
    if (saved && LANGS.some(([c]) => c === saved)) return saved;
    // 기기 언어. zh 는 간체·번체를 가른다
    const nav = (navigator.language || "ko").toLowerCase();
    if (nav.startsWith("zh")) return /tw|hk|hant/.test(nav) ? "zh-TW" : "zh-CN";
    const base = nav.split("-")[0];
    return LANGS.some(([c]) => c === base) ? base : "ko";
  }
  function chunks(text, limit) {              // 문단 경계로 limit 안쪽 토막들
    const out = []; let cur = "";
    text.split(/\n\s*\n/).forEach(p => {
      while (p.length > limit) {              // 한 문단이 한도보다 길면 문장 경계로
        const cut = Math.max(p.lastIndexOf(". ", limit), limit / 2);
        if (cur) { out.push(cur); cur = ""; }
        out.push(p.slice(0, cut + 1)); p = p.slice(cut + 1).trim();
      }
      if (cur && cur.length + p.length + 2 > limit) { out.push(cur); cur = ""; }
      cur = cur ? cur + "\n\n" + p : p;
    });
    if (cur) out.push(cur);
    return out;
  }
  // box 안에 언어 고르기 + 서비스별 링크를 그린다. text 는 넘길 글 전체
  function renderXlate(box, text) {
    const lang = xlateLang();
    const opts = LANGS.map(([c, n]) => `<option value="${c}"${c === lang ? " selected" : ""}>${n}</option>`).join("");
    let links = "";
    SERVICES.filter(s => s.ok(lang)).forEach(s => {
      const parts = chunks(text, s.limit);
      links += `<span class="xlate-svc">${s.name}` + parts.map((t, i) =>
        ` <a href="${esc(s.url(t, lang))}" target="_blank" rel="noopener">` +
        (parts.length > 1 ? `${i + 1}/${parts.length}` : "Translate") + "</a>").join("") + "</span>";
    });
    box.innerHTML = `<span class="xlate-h">🌐 Translate to</span>
      <select class="xlate-lang" aria-label="Translate to" translate="no">${opts}</select>${links}`;
    box.querySelector("select").addEventListener("change", e => {
      setCfg({ lang: e.target.value });
      renderXlate(box, text);
    });
  }
  // innerText 는 접힌 <details> 안에서 빈 글을 낸다 — 문단(<p>)을 textContent 로 모은다
  function xlateText(el) {
    const ps = el.querySelectorAll("p");
    const parts = ps.length ? [...ps].map(p => p.textContent) : [el.textContent];
    return parts.map(t => t.replace(/[ \t]+/g, " ").trim()).filter(Boolean).join("\n\n");
  }
  // [data-xlate] 를 단 요소들의 글을 문서 순서대로 모아 .xlate 상자마다 링크를 단다
  function initXlate() {
    document.querySelectorAll(".xlate").forEach(box => {
      const scope = box.closest("[data-xlate-scope]") || document;
      const text = [...scope.querySelectorAll("[data-xlate]")]
        .map(xlateText).filter(Boolean).join("\n\n");
      if (text) renderXlate(box, text); else box.remove();
    });
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
    initXlate();
  });

  window.CONFO = Object.assign(window.CONFO || {}, {
    root: ROOT,
    getBM, isBM, toggle, esc, refresh, getNote, hasNote, setNote,
    getCfg, setCfg, resetLocal, zoneNow, parseMin, fold, zonedToUtc, buildIcs, downloadIcs,
    LANGS, xlateLang, chunks, getLook, setLook,
  });
})();
