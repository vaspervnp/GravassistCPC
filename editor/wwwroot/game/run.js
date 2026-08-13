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

  // ΙΔΙΑ μηνύματα και ΙΔΙΑ σειρά προτεραιότητας με το hint_pick του
  // src/main.asm — αλλιώς το μήνυμα υπόσχεται κάτι που το πλήκτρο δεν κάνει.
  // Είναι ΟΔΗΓΟΣ: σβήνουν μετά την HINT_ROOMS-οστή αίθουσα.
  const HINT_ROOMS = 10;
  let msgLeft = 0;                    // frames που μένουν σε μήνυμα-γεγονός

  function hintFor(h) {
    if (roomNumberOf(curName) > HINT_ROOMS) return "";
    const T = D.TYPE_NAMES;
    const sc = h.supportCell();
    const st = sc ? h.room.cell(sc[0], sc[1]) : 0;
    const [bc, br] = h.bodyCell();
    const bt = h.room.cell(bc, br);

    if (bt === T.indexOf("EXIT")) return "Up or down to exit room";
    if (st === T.indexOf("LOCK")) {
      const kid = h.room.attr(sc[0], sc[1]);
      return h.keys[kid] ? "Up or down to unlock"
                         : "You need the matching key";
    }
    if (bt === T.indexOf("TELEPORT")) return "Up or down to teleport";
    // Με γεμάτα χέρια, μήνυμα ΜΟΝΟ πάνω σε πλάκα: εκεί το άφημα κάνει κάτι
    // ορατό. Παντού αλλού θα ήταν μόνιμη υπενθύμιση, δηλαδή θόρυβος.
    if (h.carry)
      return bt === T.indexOf("PLATE") ? "Up or down to drop crate" : "";
    if (bt === T.indexOf("CRATE") || bt === T.indexOf("PLATE_DOWN"))
      return "Up or down to pick up crate";
    if (bt === T.indexOf("PLATE")) return "A crate here keeps gates opened";
    if (bt === T.indexOf("GATE_OPEN")) return "This gate is open";

    // ΚΛΕΙΣΤΗ ΠΥΛΗ ΜΠΡΟΣΤΑ: είναι στερεή, δεν στέκεσαι μέσα της — την
    // ακουμπάς. Το μήνυμα λέει ΤΙ την ανοίγει, που είναι το μόνο που δεν
    // φαίνεται κοιτάζοντάς την.
    // Είτε την ΠΑΤΑΣ (είναι στερεή, άρα πάτωμα) είτε την ακουμπάς μπροστά.
    const g = st === T.indexOf("GATE") ? sc : h.aheadCell();
    const [ac, ar] = g;
    if (h.room.cell(ac, ar) === T.indexOf("GATE")) {
      const ch = h.room.attr(ac, ar);
      // ΤΟ ΚΛΕΙΔΙ ΠΡΩΤΑ: αν το κρατάς, το «ψάξε τον διακόπτη» είναι λάθος
      // συμβουλή — η πύλη ανοίγει τώρα, με ένα πάτημα.
      if (ch && h.keys[ch]) return "Up or down to open with key";
      let sw = false, plate = false;
      for (const k in h.room.attrs) {
        if (h.room.attrs[k] !== ch) continue;
        const [c, r] = k.split(",").map(Number);
        const v = h.room.cell(c, r);
        if (D.PROPS[v] & D.F.SWITCH) sw = true;
        if (v === T.indexOf("PLATE") || v === T.indexOf("PLATE_DOWN")) plate = true;
      }
      if (sw && plate) return "A switch or a plate opens this";
      if (sw) return "Find its switch to open this";
      if (plate) return "Weigh down its plate to open";
      return "This gate has nothing to open it";
    }
    return "";
  }

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

  // Δείκτες καρέ: IDLE 0-1, WALK 2-9, FALL 10-13, LAND 14-16, DEATH 17-21.
  // Ίδια αρίθμηση με το tools/stickman.py και το src/main.asm.
  const F_LAND = 14;

  function animFrame() {
    // Η προσγείωση υπερισχύει, όπως στο af_state του src/main.asm.
    if (landLeft > 0) return F_LAND + ((landLeft - 1) >> 2);
    // >> 1 και όχι >> 2: με 4 px ανά ενημέρωση, η διαίρεση με 4 έδινε 16 px
    // ανά καρέ animation αντί για τα 8 που σχεδιάστηκαν, και ο ήρωας
    // γλιστρούσε. Ίδια αλλαγή με το af_walk του src/main.asm — τα δύο πρέπει
    // να δείχνουν το ίδιο πόδι την ίδια στιγμή.
    if (hero.state === "WALK") return 2 + ((tick >> 1) & 7);
    // Βάση 10 και όχι 18: κόπηκαν τα TURNOUT/TURNIN (καρέ 10-17) που δεν
    // ζωγραφίζονταν ποτέ. Ίδια αρίθμηση με το af_fall του src/main.asm.
    if (hero.state === "FALL") return 10 + ((tick >> 3) & 3);
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
    scoreFirst = scoreEnterRoom(roomNumberOf(name));
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
        // ΜΟΝΟ ΟΤΑΝ ΑΛΛΑΖΕΙ: το πλήκτρο μένει πατημένο και θα χρέωνε σε κάθε
        // καρέ για μία απόφαση. Ίδιος έλεγχος με το ml_gok του main.asm.
        if (g !== hero.worldG) scoreAdd(D.K.SCORE_GRAV);
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

  // --- Ήχος --------------------------------------------------------------
  //
  // Οι ΙΔΙΟΙ ήχοι με τον Amstrad (src/sfx.asm), με τους ίδιους αριθμούς:
  // περίοδος AY -> συχνότητα = 125000/περίοδος. Δεν είναι εξομοίωση του AY,
  // είναι η ίδια μελωδία με ημιτονοειδή/θόρυβο — αρκεί για να δοκιμάζεις τον
  // σχεδιασμό χωρίς emulator.
  //
  // Ο ήχος ΞΕΚΙΝΑ ΜΕ ΤΟ ΠΡΩΤΟ ΠΛΗΚΤΡΟ: οι browsers δεν αφήνουν AudioContext
  // πριν ο χρήστης αγγίξει τη σελίδα, και ένα context που ξεκίνησε
  // «suspended» μένει βουβό για πάντα χωρίς κανένα μήνυμα.
  const SFX = {
    // περίοδος, θόρυβος(0-31), ένταση(0-15), διάρκεια σε εκατοστά
    step:   [[420, 20, 5, 2]],
    switch: [[595, 0, 12, 3], [298, 0, 11, 4]],
    gate:   [[478, 0, 10, 5], [379, 0, 11, 5], [319, 0, 12, 7]],
    plate:  [[758, 18, 9, 5]],
    unlock: [[239, 0, 11, 4], [159, 0, 12, 8]],
    tele:   [[568, 0, 9, 2], [379, 0, 10, 2], [239, 0, 11, 2], [142, 0, 12, 5]],
    drop:   [[893, 14, 8, 4]],
    thud:   [[1250, 24, 13, 5], [1667, 20, 7, 6]],
    exit:   [[319, 0, 11, 5], [478, 0, 10, 8]],
    enter:  [[478, 0, 10, 5], [319, 0, 12, 8]],
    hurt:   [[1000, 8, 14, 6], [1500, 16, 10, 8]],
    over:   [[478, 0, 13, 14], [568, 0, 12, 14], [716, 0, 11, 18], [955, 0, 9, 40]],
  };

  let actx = null, noiseBuf = null, hum = null;

  function audioOn() {
    if (actx) return actx;
    const C = window.AudioContext || window.webkitAudioContext;
    if (!C) return null;
    actx = new C();
    // Ένα buffer λευκού θορύβου, ξαναχρησιμοποιείται από όλους.
    noiseBuf = actx.createBuffer(1, actx.sampleRate, actx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return actx;
  }

  function play(name) {
    const seq = SFX[name];
    if (!seq || !audioOn()) return;
    let at = actx.currentTime;
    for (const [period, noise, vol, dur] of seq) {
      const len = dur / 100;
      const g = actx.createGain();
      // Η ένταση 0-15 του AY δεν είναι γραμμική· το τετράγωνο πλησιάζει
      // αρκετά και κρατά τα σιγανά σιγανά.
      const peak = Math.pow(vol / 15, 2) * 0.25;
      g.gain.setValueAtTime(peak, at);
      g.gain.exponentialRampToValueAtTime(0.0001, at + len);
      g.connect(actx.destination);
      if (period > 0) {
        const o = actx.createOscillator();
        o.type = "square";              // ο AY βγάζει τετραγωνικό
        o.frequency.value = 125000 / period;
        o.connect(g); o.start(at); o.stop(at + len);
      }
      if (noise > 0) {
        const n = actx.createBufferSource();
        n.buffer = noiseBuf; n.loop = true;
        const f = actx.createBiquadFilter();
        f.type = "lowpass";
        f.frequency.value = 125000 / (noise * 4);   // μεγάλη περίοδος = μπάσος
        const ng = actx.createGain();
        ng.gain.value = 0.5;
        n.connect(f); f.connect(ng); ng.connect(g);
        n.start(at); n.stop(at + len);
      }
      at += len;
    }
  }

  // Τα παράσιτα της ζώνης κλειδώματος: ΣΥΝΕΧΗΣ σιγανός θόρυβος, όχι εφέ.
  function humSet(on) {
    if (on && !hum) {
      if (!audioOn()) return;
      const n = actx.createBufferSource();
      n.buffer = noiseBuf; n.loop = true;
      const f = actx.createBiquadFilter();
      f.type = "lowpass"; f.frequency.value = 1200;
      const g = actx.createGain();
      g.gain.value = 0.0;
      g.gain.linearRampToValueAtTime(0.05, actx.currentTime + 0.08);
      n.connect(f); f.connect(g); g.connect(actx.destination);
      n.start();
      hum = { n, g };
    } else if (!on && hum) {
      const h = hum; hum = null;
      h.g.gain.linearRampToValueAtTime(0.0001, actx.currentTime + 0.08);
      setTimeout(function () { try { h.n.stop(); } catch (e) {} }, 150);
    }
  }

  // --- Ρολόι με τον ρυθμό του Amstrad ------------------------------------
  // ΔΥΟ ΛΑΘΗ ΜΑΖΙ, και το δεύτερο είναι το μεγάλο.
  //
  // (1) Το requestAnimationFrame χτυπά στη συχνότητα της ΟΘΟΝΗΣ, όχι του
  //     παιχνιδιού. Με μία ενημέρωση ανά repaint η ίδια WALK_V έδινε άλλη
  //     ταχύτητα σε κάθε μηχάνημα: 120 px/s στα 60 Hz, 288 στα 144.
  //
  // (2) Ούτε τα 50 Hz είναι η σωστή απάντηση. Ο βρόχος του Amstrad ΔΕΝ
  //     χωράει σε ένα καρέ — θέλει 4 vsyncs όταν περπατάς — οπότε το σίδερο
  //     τρέχει 12,5 ενημερώσεις/s και δίνει 50 px/s. Κλειδώνοντας εδώ στα
  //     ονομαστικά 50 Hz ο editor έβγαζε 200 px/s: τετραπλάσια, και η δοκιμή
  //     έλεγε πάλι ψέματα, απλώς σταθερά αντί για ανά μηχάνημα.
  //
  // Γι' αυτό ΤΟ ΒΗΜΑ ΔΗΛΩΝΕΙ ΤΟ ΚΟΣΤΟΣ ΤΟΥ: η fn επιστρέφει πόσα vsyncs
  // έφαγε στον CPC (0 = σταμάτα). Οι τιμές είναι μετρημένες — δες το
  // CPC_VSYNC_* στο tools/physics.py.
  const VSYNC_MS = 1000 / 50;
  const STEP_MAX = 5;        // πόσα βήματα το πολύ σε ένα repaint

  function cpcClock(fn) {
    let due = null;                     // πότε οφείλεται το επόμενο βήμα
    (function pump(now) {
      if (due === null) due = now;
      // ΦΡΑΓΜΑ: σε κρυμμένη καρτέλα το rAF παγώνει και το ρολόι μένει πίσω
      // δεκάδες δευτερόλεπτα. Χωρίς αυτό, γυρίζοντας θα έτρεχαν χιλιάδες
      // βήματα με ακίνητη εικόνα — ο ήρωας θα «τηλεμεταφερόταν».
      const back = VSYNC_MS * D.K.CPC_VSYNC_RUN * STEP_MAX;
      if (now - due > back) due = now - back;
      let cost = 1;
      while (cost && now >= due) { cost = fn(); due += VSYNC_MS * cost; }
      if (cost) requestAnimationFrame(pump);
    })(performance.now());
  }

  // --- ΣΚΟΡ -------------------------------------------------------------
  // Μεταγραφή του src/score.asm. ΔΥΟ ΠΥΛΕΣ, όχι μία:
  //   - τα θετικά μόνο στην ΠΡΩΤΗ επίσκεψη κάθε αίθουσας
  //   - και οι επαναλήψιμες ενέργειες (διακόπτης, πύλη, λουκέτο, πλάκα) μία
  //     φορά ανά αίθουσα ΑΝΑ ΕΙΔΟΣ, αλλιώς γυρίζεις τον ίδιο διακόπτη σε βρόχο
  //   - τα αρνητικά μετράνε πάντα
  // Τα κλειδιά και τα κιβώτια είναι ανά τεμάχιο: καταναλώνονται.
  const ONCE_PER_ROOM = { switch: "SCORE_SWITCH", gate: "SCORE_GATE",
                          lock: "SCORE_LOCK", plate: "SCORE_PLATE",
                          paraland: "SCORE_PARA_LAND" };
  const PER_ITEM = { key: "SCORE_PICKUP", crate: "SCORE_PICKUP" };

  let score = 0, visited = new Set(), roomAwarded = new Set();

  // ΤΑ ΔΙΑΒΑΖΟΥΜΕ ΔΥΝΑΜΙΚΑ, οπότε το grep του tools/genjs.py δεν τα βλέπει:
  // ένα ξεχασμένο export θα έδινε undefined, το undefined θα έκανε το σκορ
  // NaN, και το NaN δεν είναι ούτε αρνητικό — το παιχνίδι θα συνέχιζε με
  // κενή ένδειξη. Ο έλεγχος γίνεται μία φορά και φωνάζει δυνατά.
  for (const k of [...Object.values(ONCE_PER_ROOM), ...Object.values(PER_ITEM),
                   "SCORE_START", "SCORE_EXIT", "SCORE_PARA_KEEP",
                   "SCORE_STEP", "SCORE_GRAV"])
    if (typeof D.K[k] !== "number")
      throw new Error("λείπει η σταθερά σκορ " + k + " από το data.js");

  function scoreReset() {
    score = D.K.SCORE_START;
    visited = new Set();
    roomAwarded = new Set();
  }

  function scoreEnterRoom(n) {
    roomAwarded = new Set();
    if (visited.has(n)) return false;   // ξαναμπήκες: τα θετικά κλείνουν
    visited.add(n);
    return true;
  }

  function scoreAdd(points) {
    score += points;
    // ΑΡΝΗΤΙΚΟ = ΤΕΛΟΣ, με δικό του λόγο — όχι μηδενίζοντας την ενέργεια.
    if (score < 0 && !ended) { ended = "GAME OVER"; play("over"); }
  }

  function scoreAward(points, kind) {
    if (!scoreFirst) return;            // ξαναμπήκες σε αίθουσα που έλυσες
    if (kind) {
      if (roomAwarded.has(kind)) return;
      roomAwarded.add(kind);
    }
    scoreAdd(points);
  }

  let scoreFirst = false;   // πρώτη επίσκεψη στην ΤΡΕΧΟΥΣΑ αίθουσα;
  let landLeft = 0;         // καρέ που μένουν στο animation προσγείωσης

  // Πρόσημο και τέσσερα ψηφία, ΜΕ μηδενικά μπροστά — ίδια μορφή με το
  // score_digits του src/score.asm. Σταθερό πλάτος ώστε να μην αφήνει
  // σκουπίδι όταν το σκορ κονταίνει.
  function scoreText() {
    const n = Math.abs(score) % 10 ** D.HUD.score_digits;
    return (score < 0 ? "-" : " ") +
           String(n).padStart(D.HUD.score_digits, "0");
  }

  function scoreEvents(h) {
    for (const e of h.events) {
      if (ONCE_PER_ROOM[e]) scoreAward(D.K[ONCE_PER_ROOM[e]], e);
      else if (PER_ITEM[e]) scoreAward(D.K[PER_ITEM[e]], null);
    }
    // ΑΝΑ ΠΑΤΗΜΑ ΠΟΔΙΟΥ, όχι ανά pixel — ο ίδιος παλμός που παίζει τον ήχο.
    for (const e of h.sfx) if (e === "step") scoreAdd(D.K.SCORE_STEP);
  }

  let ended = null;          // "GAME OVER" ή "THE END" — παγώνει τον βρόχο

  // ΕΝΑ βήμα: ενημέρωση + σχεδίαση. Δεν προγραμματίζει το επόμενο — το κάνει
  // ο cpcClock. Επιστρέφει πόσα vsyncs κόστισε στον Amstrad.
  //
  // ΠΑΓΩΜΕΝΟΣ ΚΟΣΜΟΣ, ΖΩΝΤΑΝΟΣ ΒΡΟΧΟΣ. Ο βρόχος σταματούσε εντελώς στο τέλος
  // της παρτίδας, οπότε το Restart δεν είχε ποιον να ξυπνήσει: καθάριζε το
  // ended, ξανάστηνε την αίθουσα, και η εικόνα έμενε παγωμένη για πάντα. Το
  // ίδιο και η αλλαγή αίθουσας από τη λίστα.
  function freezeNote() {
    const t = ended === "GAME OVER" ? "GAME OVER — press Restart" : "THE END";
    if (note.textContent !== t) note.textContent = t;
  }

  function frame() {
    if (ended) { freezeNote(); return D.K.CPC_VSYNC_IDLE; }
    const { walk, run } = input();
    hero.update(walk, run);      // το τρέξιμο είναι ΣΗΜΑΙΑ, όχι δεύτερη ενημέρωση
    scoreEvents(hero);
    // Η κακή προσγείωση πυροδοτεί το κάθισμα, όπως το hl_dmg του hero.asm.
    if (hero.events.includes("landhard")) landLeft = D.K.LAND_TICKS * 3;
    else if (landLeft > 0) landLeft--;
    tick += run ? 2 : 1;
    for (const e of hero.sfx) play(e);
    humSet(hero.noflip());

    if (hero.paraOpen) {
      if (paraFrame < D.PARA.frames.length - 1 && ++paraTick >= PARA_TICKS) {
        paraTick = 0; paraFrame++;
      }
    } else { paraFrame = 0; paraTick = 0; }

    window.__hero = hero;               // για επιθεώρηση/έλεγχο από εργαλεία
    window.__trail = trail;
    hist.push([hero.x, hero.y]);
    if (hist.length > STUCK_FRAMES) hist.shift();

    // ΜΗΔΕΝΙΚΗ ΕΝΕΡΓΕΙΑ = τέλος. Στον Amstrad βγαίνει η οθόνη GAME OVER με τα
    // γράμματα του τίτλου· εδώ αρκεί το μήνυμα.
    //
    // ΜΕ ΣΗΜΑΙΑ, όχι σκέτος έλεγχος: η συνθήκη μένει αληθής, οπότε χωρίς
    // αυτήν ο ήχος θα έπαιζε εξήντα φορές το δευτερόλεπτο και το παιχνίδι θα
    // συνέχιζε να τρέχει από κάτω.
    if (hero.energy <= 0 && !ended) {
      ended = "GAME OVER";
      play("over");
    }
    if (ended) {
      freezeNote();               // η εικόνα μένει ως έχει· ο βρόχος συνεχίζει
      return D.K.CPC_VSYNC_IDLE;
    }

    if (hero.won) {
      const dest = roomDestFor(hero);
      hero.won = false;
      scoreAward(D.K.SCORE_EXIT, "exit");
      // ΑΝΑ ΑΛΕΞΙΠΤΩΤΟ που περνάει μαζί σου στην επόμενη πίστα.
      for (let i = 0; i < hero.parachute; i++)
        scoreAward(D.K.SCORE_PARA_KEEP, null);
      // ROOM_END: η πόρτα που ΚΛΕΙΝΕΙ το παιχνίδι. 255 και όχι 0, γιατί το 0
      // το γράφει κάθε πόρτα χωρίς δηλωμένο προορισμό.
      if (dest === 255) {
        ended = "THE END";
        play("enter");
        return D.K.CPC_VSYNC_IDLE;   // άλλο ένα βήμα, που τυπώνει το μήνυμα
      }
      play("exit");
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
        humSet(false);          // η ζώνη της παλιάς αίθουσας δεν ισχύει
        play("enter");
        note.textContent = "Room " + dest + (arr ? " (door arrival point)" : "");
      } else if (dest) {
        note.textContent = "Room " + dest + " does not exist";
      } else {
        note.textContent = "Exit with no declared destination";
      }
    }

    screen.clear();
    screen.tiles(room);
    // ΑΝΑΒΟΣΒΗΝΕΙ ΟΣΟ ΕΙΝΑΙ ΑΤΡΩΤΟΣ — 4 καρέ μέσα, 4 έξω, ίδιος ρυθμός με
    // τον Amstrad (bit 2 του μετρητή). Παραλείπεται μόνο ο ήρωας· η αίθουσα
    // ζωγραφίζεται κανονικά.
    if (!(hero.hurtLeft & 4)) {
      if (hero.paraOpen)
        screen.sprite(R.paraSprite(hero.g, paraFrame),
                      hero.x + G.off(hero.g, 0, -14)[0],
                      hero.y + G.off(hero.g, 0, -14)[1]);
      screen.sprite(R.heroSprite(hero.g, animFrame()), hero.x, hero.y);
    }
    screen.hud(hero);
    screen.flush();
    // Θέση από το μοντέλο, ίδια με το SCORE_COL του src/score.asm.
    screen.text(scoreText(), 1, D.HUD.score_col);

    // ΜΗΝΥΜΑ ΓΙΑ Ο,ΤΙ ΠΑΤΑΣ, στο ΑΛΛΟ μισό της οθόνης ώστε να μη σκεπάζει
    // αυτό που περιγράφει. Σκέτη σχεδίαση μετά το frame: δεν αγγίζει τη
    // φυσική και δεν εμποδίζει την κίνηση.
    // Μήνυμα-ΓΕΓΟΝΟΣ: δείχνεται ΠΑΝΤΑ, ακόμα και μετά το όριο αιθουσών —
    // είναι η μόνη φορά που μαθαίνεις ότι δεν θα χρειαστεί να πατήσεις.
    if (hero.keyAutoMsg) { hero.keyAutoMsg = false; msgLeft = 150; }
    if (msgLeft) msgLeft--;
    const hint = msgLeft ? "This key unlocks on touch" : hintFor(hero);
    if (hint) {
      const [, dr] = hero.bodyCell();
      screen.text(hint, dr < 12 ? 16 : 7,
                  Math.floor((40 - hint.length) / 2) + 1);
    }
    // Το κόστος του καρέ που μόλις έτρεξε. Η πτώση χρεώνεται σαν ακινησία:
    // δεν έχει τον βρόχο του h_walk, που είναι ό,τι ακριβό έχει το βάδισμα.
    return walk ? (run ? D.K.CPC_VSYNC_RUN : D.K.CPC_VSYNC_WALK)
                : D.K.CPC_VSYNC_IDLE;
  }

  // --- Οθόνη μενού ------------------------------------------------------
  // Ο ήρωας κάνει κύκλους μέσα σε αρένα 10x5. ΔΕΝ είναι animation: τρέχει η
  // πραγματική φυσική με walk=1 μονίμως, όπως και στον Amstrad.
  const ARENA_C = 15, ARENA_R = 9, ARENA_W = 10, ARENA_H = 5;

  // Ίδιες θέσεις με τον πίνακα menu_lines του src/menu.asm (στήλη, γραμμή).
  const MENU_LINES = [
    [2, 11, "GRAVITY"], [28, 12, "SHIFT run"],
    [28, 14, "UP/DOWN ="], [28, 15, "use  door"],
    [8, 20, "Press Space to start game"],
    [8, 23, "REVIVE8BIT - 2026 - VASPER"],
  ];
  // Δύο σελίδες πλήκτρων που εναλλάσσονται· ίδιες με τα menu_keys_* του
  // src/menu.asm, ίδιου πλάτους ώστε η μία να γράφει πάνω στην άλλη.
  const MENU_KEYS = [
    [[3, 12, "Q W E   "], [3, 13, "A   D   "], [3, 14, "Z X C   "],
     [28, 11, "M N  walk"]],
    [[3, 12, "F7 F8 F9"], [3, 13, "F4    F6"], [3, 14, "F1 F2 F3"],
     [28, 11, "< >  walk"]],
  ];
  // Three seconds per page of controls, same as MENU_PAGE in src/menu.asm.
  // COUNTED IN VSYNCS, not in mtick: one mtick is a whole CPC update, which
  // costs CPC_VSYNC_WALK vsyncs. Counting ticks would make the page length
  // depend on the frame cost, which is the bug the Amstrad side just lost.
  const MENU_PAGE_VSYNC = 3 * 50;

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
      cpcClock(frame);
    };
    addEventListener("keydown", go);
    note.textContent = "Press Space to start game";

    cpcClock(function menuFrame() {
      if (done) return 0;
      mhero.update(1);                  // ο ήρωας του μενού πάντα περπατά
      mtick++;
      screen.clear();
      screen.tiles(mroom);
      screen.title();                   // ΠΡΙΝ το flush: ίδια pixel με τον CPC
      screen.sprite(R.heroSprite(mhero.g,
        mhero.state === "WALK" ? 2 + ((mtick >> 2) & 7) : (mtick >> 5) & 1),
        mhero.x, mhero.y);
      screen.flush();
      screen.menuText(MENU_LINES);      // …και το firmware κείμενο από πάνω
      const vsyncs = mtick * D.K.CPC_VSYNC_WALK;
      screen.menuText(MENU_KEYS[Math.floor(vsyncs / MENU_PAGE_VSYNC) % 2]);
      return D.K.CPC_VSYNC_WALK;
    });
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
      for (const m of foot.matchAll(
             /(sw|gate|lock|key|plate|spikes)\s+(\d+)\s+(\d+)\s+(\d+)/gi))
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
      // Κάθε όψη και κάθε κατάσταση: ο ίδιος διακόπτης μπορεί να είναι
      // ζωγραφισμένος πατημένος ή σε οποιαδήποτε από τις τέσσερις φορές.
      for (let t = 0; t < D.NTYPES; t++)
        if (D.PROPS[t] & D.F.SWITCH) spreadKind(cells, attrs, t);
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("GATE"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("LOCK"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("KEY"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("PLATE"));
      spreadKind(cells, attrs, D.TYPE_NAMES.indexOf("PLATE_DOWN"));
      // Και τα αγκάθια: είναι στόχοι καλωδίωσης όπως οι πύλες, και στις οκτώ
      // μορφές τους (τέσσερις φορές x βγαλμένα/τραβηγμένα).
      for (const n of ["SPIKE_U", "SPIKE_L", "SPIKE_D", "SPIKE_R",
                       "SPIKE_U_OFF", "SPIKE_L_OFF", "SPIKE_D_OFF", "SPIKE_R_OFF"])
        spreadKind(cells, attrs, D.TYPE_NAMES.indexOf(n));
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
    scoreReset();
    if (!asked) { menu(want); return; }
    start(want, rooms[want].cells, rooms[want].start);
    cpcClock(frame);
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
    ended = null;
    scoreReset();       // άλλη αίθουσα από τη λίστα = άλλη παρτίδα
    if (m) start(sel.value, m.cells, m.start);
  });
  document.getElementById("restart").addEventListener("click", () => {
    const m = rooms[curName];
    if (!m) return;
    ended = null;                               // αλλιώς μένει παγωμένο
    scoreReset();
    m.cells = m.pristine.map(r => r.slice());   // καθαρή αίθουσα, όχι μισοπαιγμένη
    start(curName, m.cells, m.start);
  });

  load();
})(window.GAME_DATA, window.GRAV, window.GRAV_RENDER);
