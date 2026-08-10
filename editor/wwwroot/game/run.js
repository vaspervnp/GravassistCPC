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

  // ΣΤΟΙΒΑ ΔΙΑΔΡΟΜΗΣ — μεταγραφή του Trail του tools/physics.py.
  // Πόρτα προς δωμάτιο της στοίβας = ανοιχτή (γυρνάς πίσω). Πόρτα προς δωμάτιο
  // που ΞΕΧΕΙΛΙΣΕ = μπλοκ. Πόρτα προς δωμάτιο που δεν έχεις δει = ανοιχτή.
  const trail = { rooms: [], sealed: new Set() };

  // Ίδιο κείμενο και ίδια στήλη με το src/main.asm.
  const DOOR_MSG = "Up or down to exit room";
  const MSG_COL = 9;

  function trailEnter(current, entering) {
    const at = trail.rooms.indexOf(entering);
    if (at >= 0) {                      // γύρισες πίσω: ξετυλίγεται η στοίβα
      trail.rooms = trail.rooms.slice(at + 1);
      return;
    }
    trail.rooms.unshift(current);
    trail.sealed.delete(current);       // ξαναμπήκε στη στοίβα -> ξανανοίγει
    while (trail.rooms.length > D.K.TRAIL_MAX) trail.sealed.add(trail.rooms.pop());
  }

  // Οι σφραγισμένες πόρτες γίνονται στερεές ΣΤΟ ΑΝΤΙΓΡΑΦΟ του δωματίου και
  // ΟΧΙ στο αποθηκευμένο πλέγμα: η σφράγιση δεν είναι αλλαγή του δωματίου
  // αλλά της διαδρομής σου, και ξαναϋπολογίζεται σε κάθε είσοδο.
  let sealedCells = [];               // ποια κελιά μετατράπηκαν σε μπλοκ

  function sealDoors(meta) {
    const EX = D.TYPE_NAMES.indexOf("EXIT");
    sealedCells = [];
    for (let r = 0; r < D.ROWS; r++)
      for (let c = 0; c < D.COLS; c++)
        if (room.cells[r][c] === EX && trail.sealed.has(meta.exits[c + "," + r])) {
          room.cells[r][c] = D.TYPE_NAMES.indexOf("SOLID");
          sealedCells.push([c, r]);
        }
  }

  /// Ξηλώνει τη σφράγιση πριν αποθηκευτεί το πλέγμα του δωματίου. Χωρίς αυτό
  /// τα μπλοκ θα γράφονταν ως πραγματικά τοιχώματα και η πόρτα δεν θα
  /// ξανάνοιγε ποτέ — ενώ ο κανόνας λέει ότι ξανανοίγει.
  function unsealDoors() {
    const EX = D.TYPE_NAMES.indexOf("EXIT");
    for (const [c, r] of sealedCells) room.cells[r][c] = EX;
    sealedCells = [];
  }

  function animFrame() {
    if (hero.state === "WALK") return 2 + ((tick >> 2) & 7);
    if (hero.state === "FALL") return 18 + ((tick >> 3) & 3);
    return (tick >> 5) & 1;
  }

  function start(name, cells, startPos, keep) {
    curName = name;
    room = new G.Room(cells, (rooms[name] || {}).teleports,
                     (rooms[name] || {}).attrs);
    hero = new G.Hero(room, startPos[0], startPos[1], startPos[2]);
    // Ο ΠΑΙΚΤΗΣ ΚΡΑΤΑΕΙ Ο,ΤΙ ΚΟΥΒΑΛΑΕΙ. Ο νέος ήρωας ξεκινούσε με γεμάτη
    // ενέργεια και άδεια χέρια, οπότε κάθε πόρτα ήταν και μια δωρεάν γέμιση —
    // και το κιβώτιο που κρατούσες εξαφανιζόταν.
    if (keep) {
      hero.energy = keep.energy;
      hero.keys = keep.keys.slice();
      hero.parachute = keep.parachute;
      hero.carry = keep.carry;
    }
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
    // ΠΑΝΩ ή ΚΑΤΩ ανοίγει την πόρτα — η επαφή δεν αρκεί. Το Space μένει ως
    // εναλλακτική για τα υπόλοιπα (λουκέτο, τηλεμεταφορά, κιβώτιο).
    const use = keys.has("ArrowDown") || keys.has("ArrowUp") || keys.has("Space");
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
    window.__trail = trail;
    hist.push([hero.x, hero.y]);
    if (hist.length > STUCK_FRAMES) hist.shift();

    if (hero.won) {
      const dest = roomDestFor(hero);
      hero.won = false;
      if (dest && rooms["room_" + dest + ".txt"]) {
        const from = roomNumberOf(curName);
        const nr = rooms["room_" + dest + ".txt"];
        sel.value = "room_" + dest + ".txt";
        // Το αν υπάρχει σημείο άφιξης το κρίνει η πόρτα από την οποία ΒΓΑΙΝΕΙΣ
        // — όχι αυτή από την οποία μπήκες, που ζει σε άλλο αρχείο.
        // Η ΑΙΘΟΥΣΑ ΘΥΜΑΤΑΙ. Το Room αντιγράφει το πλέγμα, οπότε ό,τι
        // άλλαζε ο παίκτης ζούσε μόνο στο αντίγραφο και χανόταν με την πόρτα:
        // τα pickups αναγεννιόνταν σε κάθε επίσκεψη. Ο Amstrad το λύνει με
        // ημερολόγιο· εδώ αρκεί να κρατήσουμε το πλέγμα.
        // Πριν το write-back, ξήλωσε τη σφράγιση: αλλιώς τα μπλοκ θα
        // αποθηκεύονταν ως πραγματικά τοιχώματα του δωματίου.
        unsealDoors();
        rooms[curName].cells = room.cells;
        const arr = arrivalIn(nr, from);
        start(sel.value, nr.cells, arr || nr.start, {
            energy: hero.energy, keys: hero.keys,
            parachute: hero.parachute, carry: hero.carry,
        });
        trailEnter(from, dest);
        sealDoors(nr);
        note.textContent = "Room " + dest + (arr ? " (door arrival point)" : "");
      } else if (dest) {
        note.textContent = "Room " + dest + " does not exist";
      } else {
        note.textContent = "Exit with no declared destination";
      }
    }
    if (hero.energy === 0) note.textContent = "Out of energy — restart";

    screen.clear();
    screen.tiles(room);
    if (hero.paraOpen)
      screen.sprite(R.paraSprite(hero.g, paraFrame),
                    hero.x + G.off(hero.g, 0, -14)[0],
                    hero.y + G.off(hero.g, 0, -14)[1]);
    screen.sprite(R.heroSprite(hero.g, animFrame()), hero.x, hero.y);
    screen.hud(hero);
    screen.flush();

    // ΜΗΝΥΜΑ ΠΟΡΤΑΣ: μόνο όσο πατάς πόρτα, και στο ΑΛΛΟ μισό της οθόνης ώστε
    // να μη σκεπάζει αυτό που περιγράφει. Είναι σκέτη σχεδίαση μετά το frame:
    // δεν αγγίζει τη φυσική και δεν εμποδίζει την κίνηση.
    const [dc, dr] = hero.bodyCell();
    if (room.cell(dc, dr) === D.TYPE_NAMES.indexOf("EXIT"))
      screen.text(DOOR_MSG, dr < 12 ? 16 : 7, MSG_COL);
    requestAnimationFrame(frame);
  }

  // --- Οθόνη μενού ------------------------------------------------------
  // Ο ήρωας κάνει κύκλους μέσα σε αρένα 10x5. ΔΕΝ είναι animation: τρέχει η
  // πραγματική φυσική με walk=1 μονίμως, όπως και στον Amstrad.
  const ARENA_C = 15, ARENA_R = 9, ARENA_W = 10, ARENA_H = 5;

  function menu(firstRoom) {
    const SOLID = D.TYPE_NAMES.indexOf("SOLID");
    const cells = [];
    for (let r = 0; r < D.ROWS; r++) cells.push(new Array(D.COLS).fill(0));
    for (let r = ARENA_R; r < ARENA_R + ARENA_H; r++)
      for (let c = ARENA_C; c < ARENA_C + ARENA_W; c++)
        if (r === ARENA_R || r === ARENA_R + ARENA_H - 1 ||
            c === ARENA_C || c === ARENA_C + ARENA_W - 1)
          cells[r][c] = SOLID;

    const mroom = new G.Room(cells, {}, {});
    const mhero = new G.Hero(mroom, (ARENA_C + 3) * D.CELL + D.CELL / 2,
                             D.GRID_Y0 + (ARENA_R + 2) * D.CELL + D.CELL / 2, 0);
    let mtick = 0, done = false;
    const go = e => {
      if (e.code !== "Space" || done) return;
      done = true;
      removeEventListener("keydown", go);
      start(firstRoom, rooms[firstRoom].cells, rooms[firstRoom].start);
      requestAnimationFrame(frame);
    };
    addEventListener("keydown", go);
    note.textContent = "Press Space to start game";

    (function menuFrame() {
      if (done) return;
      mhero.update(1);
      mtick++;
      screen.clear();
      screen.tiles(mroom);
      screen.sprite(R.heroSprite(mhero.g,
        mhero.state === "WALK" ? 2 + ((mtick >> 2) & 7) : (mtick >> 5) & 1),
        mhero.x, mhero.y);
      screen.flush();
      screen.title();
      requestAnimationFrame(menuFrame);
    })();
  }

  function roomNumberOf(name) {
    const m = /^room_(\d+)\.txt$/i.exec(name || "");
    return m ? parseInt(m[1], 10) : 0;
  }

  // Πού εμφανίζεται ο παίκτης βγαίνοντας από την πόρτα της `meta` που γυρίζει
  // στην αίθουσα `origin`. Ίδια σειρά σάρωσης με το physics.arrival_for, ώστε
  // browser και Amstrad να βγάζουν το ίδιο κελί.
  function arrivalIn(meta, origin) {
    const EX = D.TYPE_NAMES.indexOf("EXIT");
    for (let r = 0; r < D.ROWS; r++)
      for (let c = 0; c < D.COLS; c++) {
        if (meta.cells[r][c] !== EX) continue;
        if (meta.exits[c + "," + r] !== origin) continue;
        // Δηλωμένη φορά βαρύτητας· χωρίς δήλωση, η αρχική της αίθουσας.
        const gd = (meta.arriveG || {})[c + "," + r];
        const g = gd === undefined ? meta.start[2] : gd;
        // Ρητά δηλωμένο σημείο άφιξης: κερδίζει το αυτόματο διπλανό κελί.
        const dec = (meta.arrive || {})[c + "," + r];
        if (dec) return [dec[0] * D.CELL + D.CELL / 2,
                         D.GRID_Y0 + dec[1] * D.CELL + D.CELL / 2, g];
        // Χωρίς δήλωση, μόνο αν η ίδια η πόρτα λέει «διπλή».
        if (!(meta.twoWay || {})[c + "," + r]) return null;
        for (const [nc, nr] of [[c-1,r],[c+1,r],[c,r-1],[c,r+1]]) {
          if (nc < 0 || nr < 0 || nc >= D.COLS || nr >= D.ROWS) continue;
          const t = meta.cells[nr][nc];
          if (t !== EX && !(D.PROPS[t] & (D.F.SOLID | D.F.DEADLY)))
            return [nc * D.CELL + D.CELL / 2,
                    D.GRID_Y0 + nr * D.CELL + D.CELL / 2, g];
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
      const twoWay = {}, arrive = {}, arriveG = {};
      // Τα προαιρετικά πεδία είναι ΘΕΣΗΣ: κελί άφιξης μετά τη σημαία διπλής,
      // φορά βαρύτητας τελευταία (χωρίς κελί δεν έχει σε τι να εφαρμοστεί).
      for (const m of foot.matchAll(
             /exit\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+([01])(?:\s+(\d+)\s+(\d+)(?:\s+([0-7]))?)?)?/gi)) {
        exits[m[1] + "," + m[2]] = +m[3];
        twoWay[m[1] + "," + m[2]] = m[4] === "1";
        if (m[5] !== undefined) arrive[m[1] + "," + m[2]] = [+m[5], +m[6]];
        if (m[7] !== undefined) arriveG[m[1] + "," + m[2]] = +m[7];
      }
      for (const m of foot.matchAll(/tp\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/gi))
        teleports[m[1] + "," + m[2]] = [+m[3], +m[4]];
      // Ιδιότητες κελιών: ΕΝΑΣ πίνακας για διακόπτες, πόρτες, κλειδαριές και
      // κλειδιά — κάθε κελί έχει ακριβώς έναν τύπο, οπότε δεν υπάρχει ασάφεια.
      const attrs = {};
      for (const m of foot.matchAll(/(sw|gate|lock|key)\s+(\d+)\s+(\d+)\s+(\d+)/gi))
        attrs[m[2] + "," + m[3]] = +m[4];
      // Γειτονικά κελιά είναι ΕΝΑ αντικείμενο: ο προορισμός σε ΟΛΑ τα κελιά.
      spread(cells, exits, D.TYPE_NAMES.indexOf("EXIT"));
      spread(cells, teleports, D.TYPE_NAMES.indexOf("TELEPORT"));
      spread(cells, twoWay, D.TYPE_NAMES.indexOf("EXIT"));
      spread(cells, arrive, D.TYPE_NAMES.indexOf("EXIT"));
      // Το arriveG ΔΕΝ απλώνεται: το spread() κρατά την πρώτη ΑΛΗΘΗ τιμή, άρα
      // θα έτρωγε τη φορά 0 (DOWN) — την πιο συνηθισμένη. Δεν χρειάζεται
      // ούτως ή άλλως: το arrivalIn σαρώνει κατά γραμμές και πέφτει πρώτα στο
      // πάνω-αριστερό κελί της ομάδας, που είναι το κλειδί της δήλωσης.
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("SWITCH"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("GATE"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("LOCK"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("KEY"));
      rooms[name] = { cells, start, exits, teleports, twoWay, arrive, arriveG,
                      attrs, pristine: cells.map(r => r.slice()) };
      const o = document.createElement("option");
      o.value = name; o.textContent = name;
      sel.appendChild(o);
    }
    // ΤΟ ΜΕΝΟΥ ΜΟΝΟ ΧΩΡΙΣ ?level=. Το κουμπί «Δοκιμή» του editor περνά πάντα
    // αίθουσα και πρέπει να μπαίνει κατευθείαν μέσα: μια οθόνη τίτλου
    // ανάμεσα σε κάθε δοκιμή σχεδίασης θα ήταν σκέτο εμπόδιο.
    const asked = new URLSearchParams(location.search).get("level");
    const want = asked
              || Object.keys(rooms).find(n => /^room_/.test(n))
              || Object.keys(rooms)[0];
    sel.value = want;
    if (!asked) { menu(want); return; }
    start(want, rooms[want].cells, rooms[want].start);
    requestAnimationFrame(frame);
  }

  // Ίδια πλημμύρα με το spread(), αλλά για τύπο που ΔΕΝ είναι έξοδος: μια
  // ψηλή πόρτα δύο κελιών είναι ΕΝΑ αντικείμενο και έχει ένα κανάλι.
  function spreadKind(cells, map, kind) { spread(cells, map, kind); }

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
    if (!m) return;
    m.cells = m.pristine.map(r => r.slice());   // καθαρή αίθουσα, όχι μισοπαιγμένη
    start(curName, m.cells, m.start);
  });

  load();
})(window.GAME_DATA, window.GRAV, window.GRAV_RENDER);
