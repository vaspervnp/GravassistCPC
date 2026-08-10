// GRAVASSIST — ο βρόχος του test run: είσοδος, animation, μετάβαση αιθουσών.
//
// Οι κανόνες εισόδου είναι ΑΚΡΙΒΩΣ του src/main.asm: πλέγμα 3x3 για τη βαρύτητα,
// καμία αλλαγή φοράς στον αέρα, δικλείδα ακινησίας, κλείδωμα με ανοιγμένο
// αλεξίπτωτο. Αν αποκλίνουν, το test run παύει να λέει την αλήθεια.
(function (D, G, R) {
  "use strict";

  const STUCK_FRAMES = 5, STUCK_PX = 6, PARA_TICKS = 5;

  // Πλέγμα 3x3: η ΘΕΣΗ του πλήκτρου είναι η κατεύθυνση.
  const GRAV_KEYS = {
    KeyX: 0, KeyZ: 1, KeyA: 2, KeyQ: 3, KeyW: 4, KeyE: 5, KeyD: 6, KeyC: 7,
    Numpad2: 0, Numpad1: 1, Numpad4: 2, Numpad7: 3,
    Numpad8: 4, Numpad9: 5, Numpad6: 6, Numpad3: 7,
  };

  const keys = new Set();
  addEventListener("keydown", e => {
    keys.add(e.code);
    if (e.code === "Space" || e.code.startsWith("Arrow")) e.preventDefault();
  });
  addEventListener("keyup", e => keys.delete(e.code));
  addEventListener("blur", () => keys.clear());

  const canvas = document.getElementById("screen");
  const screen = new R.Screen(canvas, 2);
  const note = document.getElementById("note");
  const sel = document.getElementById("level");

  let rooms = {}, hero = null, room = null, tick = 0, paraFrame = 0, paraTick = 0;
  let hist = [], usePrev = false, curName = "";

  function animFrame() {
    if (hero.state === "WALK") return 2 + ((tick >> 2) & 7);
    if (hero.state === "FALL") return 18 + ((tick >> 3) & 3);
    return (tick >> 5) & 1;
  }

  function start(name, cells, startPos) {
    curName = name;
    room = new G.Room(cells, (rooms[name] || {}).teleports);
    hero = new G.Hero(room, startPos[0], startPos[1], startPos[2]);
    tick = 0; hist = []; paraFrame = 0; paraTick = 0;
    note.textContent = "";
  }

  function stuck() {
    if (hist.length < STUCK_FRAMES) return false;
    const o = hist[0];
    return Math.abs(hero.x - o[0]) <= STUCK_PX && Math.abs(hero.y - o[1]) <= STUCK_PX;
  }

  function input() {
    let g = -1;
    for (const k in GRAV_KEYS) if (keys.has(k)) { g = GRAV_KEYS[k]; break; }
    if (g >= 0) {
      // Η ίδια ιεραρχία με το main.asm: αλεξίπτωτο > αέρας > ζώνη κλειδώματος.
      const airborne = hero.state === "FALL";
      if (!(airborne && (hero.paraOpen || !stuck()))) {
        if (!hero.noflip()) { hero.g = g; hero.state = "FALL"; }
        hero.worldG = g; hero.cratesOn = true;
      }
    }
    let walk = 0;
    if (keys.has("KeyM") || keys.has("ArrowRight")) walk = 1;
    else if (keys.has("KeyN") || keys.has("ArrowLeft")) walk = -1;
    const use = keys.has("ArrowDown") || keys.has("Space");
    if (use && !usePrev) hero.use();
    usePrev = use;
    return { walk, run: keys.has("ShiftLeft") || keys.has("ShiftRight") };
  }

  function frame() {
    const { walk, run } = input();
    hero.update(walk, run);      // το τρέξιμο είναι ΣΗΜΑΙΑ, όχι δεύτερη ενημέρωση
    tick += run ? 2 : 1;

    if (hero.paraOpen) {
      if (paraFrame < D.PARA.frames.length - 1 && ++paraTick >= PARA_TICKS) {
        paraTick = 0; paraFrame++;
      }
    } else { paraFrame = 0; paraTick = 0; }

    window.__hero = hero;               // για επιθεώρηση/έλεγχο από εργαλεία
    hist.push([hero.x, hero.y]);
    if (hist.length > STUCK_FRAMES) hist.shift();

    if (hero.won) {
      const dest = roomDestFor(hero);
      hero.won = false;
      if (dest && rooms["room_" + dest + ".txt"]) {
        const from = roomNumberOf(curName);
        const [bc, br] = hero.bodyCell();
        const two = (rooms[curName].twoWay || {})[bc + "," + br];
        const nr = rooms["room_" + dest + ".txt"];
        sel.value = "room_" + dest + ".txt";
        // Πόρτα διπλής κατεύθυνσης: εμφανίζεσαι ΔΙΠΛΑ στην πόρτα επιστροφής,
        // όχι πάνω της — εκεί θα σε ξαναπερνούσε αμέσως, ατέρμονα.
        const arr = two ? arrivalIn(nr, from) : null;
        start(sel.value, nr.cells, arr || nr.start);
        note.textContent = "Αίθουσα " + dest + (arr ? " (δίπλα στην πόρτα)" : "");
      } else if (dest) {
        note.textContent = "Η αίθουσα " + dest + " δεν υπάρχει";
      } else {
        note.textContent = "Έξοδος χωρίς δηλωμένο προορισμό";
      }
    }
    if (hero.energy === 0) note.textContent = "Χωρίς ενέργεια — επανεκκίνηση";

    screen.clear();
    screen.tiles(room);
    if (hero.paraOpen)
      screen.sprite(R.paraSprite(hero.g, paraFrame),
                    hero.x + G.off(hero.g, 0, -14)[0],
                    hero.y + G.off(hero.g, 0, -14)[1]);
    screen.sprite(R.heroSprite(hero.g, animFrame()), hero.x, hero.y);
    screen.hud(hero);
    screen.flush();
    requestAnimationFrame(frame);
  }

  function roomNumberOf(name) {
    const m = /^room_(\d+)\.txt$/i.exec(name || "");
    return m ? parseInt(m[1], 10) : 0;
  }

  // Το κελί δίπλα στην πόρτα της `meta` που γυρίζει στην αίθουσα `origin`.
  // Ίδια σειρά σάρωσης με το physics.arrival_for, ώστε να πέφτει στο ίδιο κελί.
  function arrivalIn(meta, origin) {
    const EX = D.TYPE_NAMES.indexOf("EXIT");
    for (let r = 0; r < D.ROWS; r++)
      for (let c = 0; c < D.COLS; c++) {
        if (meta.cells[r][c] !== EX) continue;
        if (meta.exits[c + "," + r] !== origin) continue;
        for (const [nc, nr] of [[c-1,r],[c+1,r],[c,r-1],[c,r+1]]) {
          if (nc < 0 || nr < 0 || nc >= D.COLS || nr >= D.ROWS) continue;
          const t = meta.cells[nr][nc];
          if (t !== EX && !(D.PROPS[t] & (D.F.SOLID | D.F.DEADLY)))
            return [nc * D.CELL + D.CELL / 2,
                    D.GRID_Y0 + nr * D.CELL + D.CELL / 2, meta.start[2]];
        }
      }
    return null;
  }

  function roomDestFor(h) {
    const [c, r] = h.bodyCell();
    const meta = rooms[curName];
    return meta && meta.exits ? (meta.exits[c + "," + r] || 0) : 0;
  }

  async function load() {
    const list = await (await fetch("/api/levels")).json();
    for (const f of list.files) {
      const name = typeof f === "string" ? f : f.name;
      const doc = await (await fetch("/api/levels/" + encodeURIComponent(name))).json();
      const cells = doc.rows.map(r => [...r].map(ch => D.CHARS[ch] ?? 0));
      // Ο δείκτης '@' διαβάζεται και το κελί μένει κενό — όπως στον φορτωτή.
      let start = [60, 44, 0];
      const gm = (doc.footer || []).join("\n").match(/gravity\s+([0-7])/i);
      const g = gm ? +gm[1] : 0;
      cells.forEach((row, r) => row.forEach((v, c) => {
        if (v === D.TYPE_NAMES.indexOf("START")) {
          row[c] = 0;
          start = [c * D.CELL + D.CELL / 2, D.GRID_Y0 + r * D.CELL + D.CELL / 2, g];
        }
      }));
      const foot = (doc.footer || []).join("\n");
      const exits = {}, teleports = {};
      const twoWay = {};
      for (const m of foot.matchAll(/exit\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+([01]))?/gi)) {
        exits[m[1] + "," + m[2]] = +m[3];
        twoWay[m[1] + "," + m[2]] = m[4] === "1";
      }
      for (const m of foot.matchAll(/tp\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/gi))
        teleports[m[1] + "," + m[2]] = [+m[3], +m[4]];
      // Γειτονικά κελιά είναι ΕΝΑ αντικείμενο: ο προορισμός σε ΟΛΑ τα κελιά.
      spread(cells, exits, D.TYPE_NAMES.indexOf("EXIT"));
      spread(cells, teleports, D.TYPE_NAMES.indexOf("TELEPORT"));
      spread(cells, twoWay, D.TYPE_NAMES.indexOf("EXIT"));
      rooms[name] = { cells, start, exits, teleports, twoWay };
      const o = document.createElement("option");
      o.value = name; o.textContent = name;
      sel.appendChild(o);
    }
    const want = new URLSearchParams(location.search).get("level")
              || Object.keys(rooms).find(n => /^room_/.test(n))
              || Object.keys(rooms)[0];
    sel.value = want;
    start(want, rooms[want].cells, rooms[want].start);
    requestAnimationFrame(frame);
  }

  function spread(cells, exits, EX) {
    const seen = new Set();
    for (let r = 0; r < D.ROWS; r++)
      for (let c = 0; c < D.COLS; c++) {
        if (cells[r][c] !== EX || seen.has(c + "," + r)) continue;
        const grp = [], st = [[c, r]];
        seen.add(c + "," + r);
        while (st.length) {
          const [cc, rr] = st.pop();
          grp.push([cc, rr]);
          for (const [nc, nr] of [[cc+1,rr],[cc-1,rr],[cc,rr+1],[cc,rr-1]])
            if (nc >= 0 && nr >= 0 && nc < D.COLS && nr < D.ROWS
                && !seen.has(nc + "," + nr) && cells[nr][nc] === EX) {
              seen.add(nc + "," + nr); st.push([nc, nr]);
            }
        }
        const dest = grp.map(([a, b]) => exits[a + "," + b]).find(v => v) || 0;
        for (const [a, b] of grp) exits[a + "," + b] = dest;
      }
  }

  sel.addEventListener("change", () => {
    const m = rooms[sel.value];
    if (m) start(sel.value, m.cells, m.start);
  });
  document.getElementById("restart").addEventListener("click", () => {
    const m = rooms[curName];
    if (m) start(curName, m.cells, m.start);
  });

  load();
})(window.GAME_DATA, window.GRAV, window.GRAV_RENDER);
