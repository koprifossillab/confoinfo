/* confoinfo — 이 기기에 반입한 학회 (P02). 읽개 하나를 반입 화면·반입 학회 화면·내 계획·첫 화면이 같이 쓴다
   (GSM 개인 레이어의 personal.js 와 같은 까닭 — 읽는 법이 갈라지면 "반입은 됐는데 화면이 다르다" 가 생긴다).

   형식은 저장소의 conferences/*.json 과 같은 confoinfo/1 (docs/data-format.md · docs/ai-guide.md).
   검사는 loader.validate 를 옮긴 것이다 — 고칠 때 둘을 같이 고친다. 화면 문구라 메시지는 영어다.
   저장은 IndexedDB. 서버로 가지 않는다. */
(function () {
  const FORMAT = "confoinfo/1";
  const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,39}$/;
  const TIME_RE = /^\d{1,2}:\d{2}$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  const LANG_RE = /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$/;
  const KINDS = ["talk", "plenary", "keynote", "poster", "break", "event"];
  const UNBOOKMARKABLE = new Set(["break"]);
  // urls.RESERVED 와 같다 — 이 이름은 사이트의 다른 화면이 쓴다
  const RESERVED = new Set(["search", "plan", "settings", "static", "talks.json", "search.json", "404.html",
    "i18n", "manifest.webmanifest", "sw.js", "names.json", "import", "local", "format.txt",
    "confoinfo-1.schema.json"]);

  function okDate(s) {
    if (!DATE_RE.test(s || "")) return false;
    const d = new Date(s + "T00:00:00Z");
    return !isNaN(d) && d.toISOString().slice(0, 10) === s;
  }
  function okZone(tz) {
    try { new Intl.DateTimeFormat("en", { timeZone: tz }); return !!tz; } catch (e) { return false; }
  }

  // ── 검사 (loader.validate) ───────────────────────────────────────────
  // published: 사이트에 이미 있는 학회 slug — 같은 학회가 두 번 뜨지 않게 받지 않는다
  function validate(data, published) {
    const errors = [], warnings = [];
    if (!data || typeof data !== "object" || Array.isArray(data)) return { errors: ["The file is not a JSON object."], warnings };
    if (data.format !== FORMAT) errors.push(`"format" must be "${FORMAT}" (found ${JSON.stringify(data.format)}).`);
    const conf = data.conference || {};
    const slug = conf.slug || "";
    if (!SLUG_RE.test(slug)) errors.push(`conference.slug must be lowercase letters, digits and hyphens, up to 40 (found ${JSON.stringify(slug)}).`);
    else if (RESERVED.has(slug)) errors.push(`conference.slug "${slug}" is used by another page of this site. Pick another.`);
    else if (published && published.includes(slug)) errors.push(`"${slug}" is already published on Confoinfo — open it from the conference list instead.`);
    ["short_name", "name"].forEach(f => { if (!conf[f]) errors.push(`conference.${f} is empty.`); });
    if (!okZone(conf.timezone)) errors.push(`conference.timezone must be an IANA name like "Asia/Seoul" (found ${JSON.stringify(conf.timezone)}).`);
    ["start_date", "end_date"].forEach(f => {
      if (conf[f] && !okDate(conf[f])) errors.push(`conference.${f} must be YYYY-MM-DD (found ${JSON.stringify(conf[f])}).`);
    });
    if (conf.language && !LANG_RE.test(conf.language)) errors.push(`conference.language must look like "en", "ko" or "zh-CN" (found ${JSON.stringify(conf.language)}).`);
    if (conf.lunch_at && !TIME_RE.test(conf.lunch_at)) errors.push(`conference.lunch_at must be HH:MM (found ${JSON.stringify(conf.lunch_at)}).`);
    if (conf.color && !/^#[0-9a-fA-F]{6}$/.test(conf.color)) warnings.push(`conference.color should be #rrggbb — the default color is used.`);

    function list(name) {
      const v = data[name];
      if (v == null) return [];
      if (!Array.isArray(v)) { errors.push(`"${name}" must be a list.`); return []; }
      return v;
    }
    function unique(items, field, what) {
      const seen = new Set();
      items.forEach((it, i) => {
        const k = it && it[field];
        if (!k) errors.push(`${what}[${i}].${field} is empty.`);
        else if (seen.has(k)) errors.push(`Two ${what} have the same ${field}: ${JSON.stringify(k)}.`);
        seen.add(k);
      });
      return seen;
    }
    const roomsIn = list("rooms"), sessionsIn = list("sessions"), absIn = list("abstracts"), talksIn = list("talks");
    const rooms = unique(roomsIn, "name", "rooms");
    const sessions = unique(sessionsIn, "code", "sessions");
    const abstracts = unique(absIn, "key", "abstracts");
    absIn.forEach(a => {
      if (!a.title) errors.push(`Abstract ${JSON.stringify(a.key)} has no title.`);
      if (a.session && !sessions.has(a.session)) warnings.push(`Abstract ${JSON.stringify(a.key)}: session ${JSON.stringify(a.session)} is not in "sessions" — shown without a session.`);
    });
    unique(talksIn, "key", "talks");
    const newRooms = new Set();
    talksIn.forEach(t => {
      const k = JSON.stringify(t.key);
      if (!t.date) errors.push(`Talk ${k} has no date.`);
      else if (!okDate(t.date)) errors.push(`Talk ${k}: date must be YYYY-MM-DD (found ${JSON.stringify(t.date)}).`);
      if (!TIME_RE.test(t.start || "")) errors.push(`Talk ${k}: start must be HH:MM (found ${JSON.stringify(t.start)}).`);
      if (t.end && !TIME_RE.test(t.end)) errors.push(`Talk ${k}: end must be HH:MM (found ${JSON.stringify(t.end)}).`);
      if (!t.title) errors.push(`Talk ${k} has no title.`);
      if (!KINDS.includes(t.kind || "talk")) errors.push(`Talk ${k}: kind must be one of ${KINDS.join(", ")} (found ${JSON.stringify(t.kind)}).`);
      if (t.room && !rooms.has(t.room)) newRooms.add(t.room);
      if (t.session && !sessions.has(t.session)) warnings.push(`Talk ${k}: session ${JSON.stringify(t.session)} is not in "sessions" — shown without a session.`);
      if (t.abstract && !abstracts.has(t.abstract)) errors.push(`Talk ${k}: abstract ${JSON.stringify(t.abstract)} is not in "abstracts".`);
    });
    [...newRooms].sort().forEach(r => warnings.push(`Room ${JSON.stringify(r)} is not in "rooms" — added at the end.`));
    if (!talksIn.length && !absIn.length) warnings.push(`No talks and no abstracts — nothing to show.`);
    return { errors, warnings };
  }

  // ── 발표 pk (loader.stable_id) ───────────────────────────────────────
  // sha1("slug/key") 앞 13자리 = 52비트 — JS 의 Number 로도 정확하다. 구운 학회와 같은 식이라
  // 나중에 그 학회가 정식으로 올라가도 북마크가 이어진다
  async function stableId(slug, key) {
    const buf = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(`${slug}/${key}`));
    const hex = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
    return parseInt(hex.slice(0, 13), 16);
  }

  // 화면이 쓰기 좋게 정리한다 — 룸 덧붙이기(loader.load 와 같다), 발표 pk, 모르는 세션 걷기
  async function prepare(data) {
    const d = JSON.parse(JSON.stringify(data));
    const slug = d.conference.slug;
    d.rooms = (d.rooms || []).slice();
    const known = new Set(d.rooms.map(r => r.name));
    d.talks = d.talks || []; d.sessions = d.sessions || []; d.abstracts = d.abstracts || [];
    d.talks.forEach(t => { if (t.room && !known.has(t.room)) { d.rooms.push({ name: t.room }); known.add(t.room); } });
    const codes = new Set(d.sessions.map(s => s.code));
    d.talks.forEach(t => { if (t.session && !codes.has(t.session)) t.session = null; t.kind = t.kind || "talk"; });
    d.abstracts.forEach(a => { if (a.session && !codes.has(a.session)) a.session = null; });
    for (const t of d.talks) t.id = await stableId(slug, t.key);
    return d;
  }

  // ── 휴식 (views.derive_breaks) ───────────────────────────────────────
  const MIN_BREAK_MIN = 10, LUNCH_MIN = 40, LUNCH_BEFORE = 60, LUNCH_AFTER = 150;
  function mins(s) { const m = TIME_RE.exec(s || "") && s.split(":"); return m ? +m[0] * 60 + +m[1] : null; }
  function breakLabel(s, e, l) {
    if (s <= l && l <= e) return "Lunch";
    if (e - s >= LUNCH_MIN && s >= l - LUNCH_BEFORE && e <= l + LUNCH_AFTER) return "Lunch";
    return "Break";
  }
  function deriveBreaks(items, lunchAt) {
    const l = mins(lunchAt || "12:30");
    const ts = items.filter(t => t.start && t.end).sort((a, b) => mins(a.start) - mins(b.start));
    const out = [];
    for (let i = 1; i < ts.length; i++) {
      const a = ts[i - 1], b = ts[i], ae = mins(a.end), bs = mins(b.start);
      if (bs > ae && bs - ae >= MIN_BREAK_MIN) out.push({ start: a.end, end: b.start, label: breakLabel(ae, bs, l) });
    }
    return out;
  }

  // ── 저장 (IndexedDB) ─────────────────────────────────────────────────
  const DB = "confoinfo-local", STORE = "confs";
  let dbP = null;
  function db() {
    if (!dbP) dbP = new Promise((res, rej) => {
      if (!window.indexedDB) return rej(new Error("This browser cannot store data (IndexedDB is off)."));
      const r = indexedDB.open(DB, 1);
      r.onupgradeneeded = () => r.result.createObjectStore(STORE, { keyPath: "slug" });
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
    return dbP;
  }
  async function tx(mode, fn) {
    const d = await db();
    return new Promise((res, rej) => {
      const t = d.transaction(STORE, mode), st = t.objectStore(STORE);
      const r = fn(st);
      t.oncomplete = () => res(r && "result" in r ? r.result : undefined);
      t.onerror = () => rej(t.error);
    });
  }
  // 기록 = {slug, data(prepare 한 것), orig(받은 그대로 — 내려받기용), file, bytes, saved}
  async function save(data, file, bytes) {
    const rec = { slug: data.conference.slug, data: await prepare(data), orig: data,
                  file: file || "", bytes: bytes || 0, saved: new Date().toISOString() };
    await tx("readwrite", st => st.put(rec));
    try { new BroadcastChannel("confoinfo-local").postMessage("changed"); } catch (e) { /* 없으면 그만 */ }
    return rec;
  }
  async function all() { try { return (await tx("readonly", st => st.getAll())) || []; } catch (e) { return []; } }
  async function get(slug) { try { return await tx("readonly", st => st.get(slug)); } catch (e) { return null; } }
  async function remove(slug) { await tx("readwrite", st => st.delete(slug)); }

  // ── 화면에 넘기는 것 ─────────────────────────────────────────────────
  const ROOT = (window.CONFO && window.CONFO.root) || "/";
  function url(slug, extra) {
    const q = new URLSearchParams(Object.assign({ c: slug }, extra || {}));
    return ROOT + "local/?" + q.toString();
  }
  // 내 계획(views.talks_json 과 같은 꼴) — 북마크한 것을 고르는 것은 plan.html 이 한다
  async function talksPayload(slugFilter) {
    const talks = [], breaks = [];
    for (const rec of await all()) {
      const d = rec.data, c = d.conference;
      if (slugFilter && c.slug !== slugFilter) continue;
      const rooms = new Map(d.rooms.map(r => [r.name, r]));
      d.talks.forEach(t => {
        if (UNBOOKMARKABLE.has(t.kind)) return;
        const r = rooms.get(t.room) || {};
        talks.push({ id: t.id, conf: c.slug, conf_name: c.short_name, tz: c.timezone, date: t.date,
          room: t.room || "", floor: r.floor || "", session: t.session || "", start: t.start, end: t.end || "",
          code: t.code || "", title: t.title, author: t.speaker || "", kind: t.kind,
          url: url(c.slug, { talk: t.key }), local: true });
      });
      const grouped = new Map();
      d.talks.forEach(t => { if (t.room) { const k = t.date + "|" + t.room; (grouped.get(k) || grouped.set(k, []).get(k)).push(t); } });
      grouped.forEach((items, k) => {
        const [date, room] = k.split("|");
        const found = items.filter(t => t.kind === "break" && t.end).map(t => ({ start: t.start, end: t.end, label: t.title }))
          .concat(deriveBreaks(items, c.lunch_at));
        found.forEach(b => breaks.push({ conf: c.slug, date, room, start: b.start, end: b.end, label: b.label }));
      });
    }
    return { talks, breaks };
  }

  // 저장소 어림 (GSM 131) — 크기는 반입한 파일의 바이트, 전체는 브라우저가 알려 주는 것
  async function usage() {
    try { const e = await navigator.storage.estimate(); return { used: e.usage || 0, quota: e.quota || 0 }; }
    catch (e) { return { used: 0, quota: 0 }; }
  }
  async function persist() {
    try { return navigator.storage && navigator.storage.persist ? await navigator.storage.persist() : false; }
    catch (e) { return false; }
  }

  window.CONFO = Object.assign(window.CONFO || {}, {
    local: { FORMAT, KINDS, validate, prepare, stableId, deriveBreaks, save, all, get, remove, url,
             talksPayload, usage, persist, UNBOOKMARKABLE },
  });
})();
