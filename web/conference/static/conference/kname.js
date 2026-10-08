/* 한글로 친 이름을 로마자 저자 이름과 맞춘다 (007).

   "최경식" → "Kyungsik Choi". 한국 이름의 로마자 표기는 사람마다 다르다 — 최: Choi·Choe,
   경: Kyung·Kyeong·Gyeong, 정: Jung·Jeong·Chung. 그래서 두 가지로 맞춘다.

   1. 성은 흔히 쓰는 표기를 표로 댄다 (이: Lee·Yi·Rhee·Rhie 처럼 규칙으로 안 나오는 것이 많다)
   2. 이름은 양쪽을 "뼈대"(skel)로 줄여 비교한다 — 표기가 갈리는 자리(eo/u/o, k/g, j/ch, l/r,
      ee/i, 띄어쓰기·하이픈)를 한 글자로 접는다. 한글은 국어의 로마자 표기법으로 옮긴 뒤 같은
      뼈대로 줄인다.

   느슨하게 접으므로 다른 이름이 걸릴 수 있다(구·고 · 유·요). 이름 검색은 놓치는 것보다
   더 걸리는 편이 낫다 — 결과를 사람이 본다. */
(function () {
  const INI = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"];
  const MED = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we",
               "wi", "yu", "eu", "ui", "i"];
  const FIN = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p",
               "t", "t", "ng", "t", "t", "k", "t", "p", "t"];

  // 흔한 성의 로마자 표기. 표에 없는 성은 로마자 표기법으로 옮긴 것 하나로 본다
  const SURNAME = {
    "김": "kim gim", "이": "lee yi rhee rhie li ri", "박": "park pak bak", "최": "choi choe",
    "정": "jung jeong chung jong", "강": "kang gang", "조": "cho jo joe", "윤": "yoon yun",
    "장": "jang chang", "임": "lim im rim", "한": "han", "오": "oh o", "서": "seo suh so",
    "신": "shin sin", "권": "kwon gwon", "황": "hwang", "안": "ahn an", "송": "song",
    "류": "ryu yoo yu lyu", "유": "yoo yu", "전": "jeon jun chun", "홍": "hong", "고": "ko go koh",
    "문": "moon mun", "양": "yang", "손": "son sohn", "배": "bae", "백": "baek paik baik",
    "허": "heo huh hur", "남": "nam", "노": "noh roh no", "하": "ha", "곽": "kwak gwak",
    "성": "sung seong", "차": "cha", "주": "joo ju chu", "우": "woo u", "구": "koo ku gu",
    "민": "min", "진": "jin chin", "지": "ji chi", "엄": "um eom", "채": "chae", "원": "won",
    "천": "cheon chun", "방": "bang", "공": "kong gong", "현": "hyun hyeon", "함": "ham",
    "변": "byun byeon", "염": "yeom yum", "여": "yeo yu", "추": "choo chu", "도": "do doh",
    "소": "so", "석": "seok suk", "선": "sun seon", "설": "seol sul", "마": "ma", "길": "gil kil",
    "표": "pyo", "명": "myung myeong", "기": "ki gi", "반": "ban", "왕": "wang", "금": "keum geum kum",
    "옥": "ok", "육": "yook yuk", "인": "in", "맹": "maeng", "제": "je", "모": "mo", "탁": "tak",
    "국": "kook guk", "어": "eo", "은": "eun", "편": "pyun pyeon", "용": "yong", "예": "ye",
    "경": "kyung kyeong", "봉": "bong", "사": "sa", "부": "boo bu", "태": "tae", "목": "mok",
    "형": "hyung hyeong", "계": "kye gye", "피": "pi", "두": "doo du", "감": "kam gam",
    "음": "eum", "빈": "bin", "동": "dong", "온": "on", "호": "ho", "범": "bum beom",
    "승": "seung", "상": "sang", "시": "si", "단": "dan", "견": "kyun gyeon", "당": "dang", "위": "wi",
    "남궁": "namgung namkung", "황보": "hwangbo", "제갈": "jegal", "선우": "sunwoo seonu",
    "독고": "dokgo", "사공": "sagong",
  };
  const COMPOUND = ["남궁", "황보", "제갈", "선우", "독고", "사공"];

  const HANGUL = /[가-힣]/;
  function isHangul(s) { return HANGUL.test(s || ""); }

  function romanize(s) {                       // 국어의 로마자 표기법, 음절마다 (소리 바뀜은 안 본다)
    let out = "";
    for (const ch of s) {
      const c = ch.charCodeAt(0) - 0xAC00;
      if (c < 0 || c > 11171) continue;
      out += INI[Math.floor(c / 588)] + MED[Math.floor((c % 588) / 28)] + FIN[c % 28];
    }
    return out;
  }

  const FOLD = [["yeo", "yo"], ["yu", "yo"], ["eo", "o"], ["ou", "o"], ["oo", "u"], ["ee", "i"],
                ["eu", "u"], ["ui", "i"], ["ae", "e"], ["oe", "e"], ["wo", "o"], ["sh", "s"],
                ["ch", "c"], ["j", "c"], ["k", "g"], ["t", "d"], ["p", "b"], ["l", "r"], ["u", "o"]];
  function skel(latin) {
    let s = (latin || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z]/g, "");
    for (const [a, b] of FOLD) s = s.split(a).join(b);
    return s.replace(/(.)\1+/g, "$1");         // 겹친 글자 하나로 (kk·ss·oo 가 접힌 뒤)
  }

  // 한글 질의 → 뼈대 해석들 [{sur, given}] — given 이 "" 이면 성만 친 것
  function queryKeys(q) {
    const s = (q || "").replace(/[^가-힣]/g, "");
    if (!s) return [];
    const out = [];
    const twoSur = s.length >= 3 && COMPOUND.includes(s.slice(0, 2));
    const surH = twoSur ? s.slice(0, 2) : s[0];
    const given = s.slice(surH.length);
    const surs = (SURNAME[surH] || romanize(surH)).split(" ");
    surs.forEach(v => out.push({ sur: skel(v), given: given ? skel(romanize(given)) : "" }));
    if (s.length >= 2 && !twoSur) out.push({ sur: "", given: skel(romanize(s)) });   // 이름만 친 것 ("경식")
    return out;
  }

  // 저자 이름 → 뼈대 해석들. "Kyungsik Choi"(이름 성)와 "Choi Kyungsik"(성 이름) 둘 다
  const cache = new Map();
  function nameKeys(name) {
    if (cache.has(name)) return cache.get(name);
    const t = (name || "").split(/[\s,]+/).filter(Boolean);
    const keys = [];
    if (t.length >= 2) {
      keys.push({ sur: skel(t[t.length - 1]), given: skel(t.slice(0, -1).join("")) });
      keys.push({ sur: skel(t[0]), given: skel(t.slice(1).join("")) });
    }
    cache.set(name, keys);
    return keys;
  }

  function matches(name, qkeys) {
    const nk = nameKeys(name);
    return qkeys.some(q => nk.some(n =>
      q.sur && q.given ? n.sur === q.sur && n.given === q.given
        : q.sur ? n.sur === q.sur
        : n.given === q.given));
  }

  window.KNAME = { isHangul, romanize, skel, queryKeys, nameKeys, matches };
})();
