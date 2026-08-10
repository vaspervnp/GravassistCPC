namespace GravassistEditor.Models;

/// <summary>
/// Ένας τύπος κελιού της πίστας.
///
/// ΤΟ ΜΟΝΟ ΣΗΜΕΙΟ όπου ορίζονται οι τύποι είναι ο πίνακας <see cref="TileCatalog.All"/>
/// πιο κάτω. Ο controller, ο parser, η παλέτα και ο renderer του view διαβάζουν ΟΛΟΙ
/// από εκεί — προσθέτοντας μία εγγραφή στον πίνακα εμφανίζεται αυτόματα νέο εργαλείο
/// στην παλέτα, νέο έγκυρο σύμβολο για τον parser και νέο σχήμα στο πλέγμα.
/// </summary>
/// <param name="Symbol">Ο χαρακτήρας στο αρχείο .txt — πρέπει να ταιριάζει με το CHARS του tools/physics.py.</param>
/// <param name="Id">Σταθερό αγγλικό αναγνωριστικό (χρησιμοποιείται σε ids του SVG και στο JSON).</param>
/// <param name="Group">Ελληνικός τίτλος κατηγορίας — ομαδοποιεί τα κουμπιά της παλέτας.</param>
/// <param name="Name">Ελληνικό όνομα για την παλέτα.</param>
/// <param name="Hint">Ελληνική επεξήγηση (tooltip) — τι κάνει το κελί.</param>
/// <param name="Fill">Χρώμα σώματος (αντικαθιστά το var(--fill) μέσα στο <paramref name="Svg"/>).</param>
/// <param name="Edge">Χρώμα ακμής (αντικαθιστά το var(--edge) μέσα στο <paramref name="Svg"/>).</param>
/// <param name="Svg">
/// Σχήμα του κελιού σε σύστημα συντεταγμένων 8x8 (= ένα tile 8x8 pixel του CPC,
/// με το y να δείχνει προς τα κάτω, όπως στο physics.py). Χρησιμοποίησε
/// var(--fill) και var(--edge) για τα χρώματα· αντικαθίστανται κατά το render.
/// Κενό string = δεν ζωγραφίζεται τίποτα (φαίνεται το φόντο).
/// </param>
public sealed record TileType(
    char Symbol,
    string Id,
    string Group,
    string Name,
    string Hint,
    string Fill,
    string Edge,
    string Svg);

/// <summary>Η παλέτα του παιχνιδιού (docs/concept-art.md §5, MODE 1 — 4 pens).</summary>
public static class Palette
{
    public const string Background = "#000080";   // pen 0, ink 1  — σκούρο μπλε
    public const string Ink = "#FFFFFF";          // pen 1, ink 26 — φωτεινό λευκό
    public const string Material = "#00FF00";     // pen 2, ink 18 — φωτεινό πράσινο
    public const string EdgeColor = "#FF8000";    // pen 3, ink 16 — πορτοκαλί
}

/// <summary>
/// Ο κατάλογος των τύπων κελιών. Κρατιέται σε αντιστοιχία με το CHARS του
/// tools/physics.py — ό,τι δέχεται εκεί ο parser, πρέπει να ζωγραφίζεται κι εδώ.
///
/// ΠΩΣ ΠΡΟΣΘΕΤΩ ΝΕΟ ΤΥΠΟ:
///   1. Πρόσθεσε μία εγγραφή <c>new TileType(...)</c> στον πίνακα <see cref="All"/>.
///   2. Διάλεξε χαρακτήρα που ΔΕΝ είναι ήδη σε χρήση και ΔΕΝ είναι το ';'
///      (ξεκινάει σχόλιο) ούτε κενό.
///   3. Πρόσθεσε τον ίδιο χαρακτήρα και στο CHARS του tools/physics.py, αλλιώς ο
///      parser της Python θα απορρίψει τη γραμμή.
/// Τίποτα άλλο δεν χρειάζεται αλλαγή — ούτε το view, ούτε ο controller.
///
/// ΣΥΜΒΑΣΗ ΚΑΤΕΥΘΥΝΣΕΩΝ: όπως στο FACING του physics.py, οι κωδικοί βαρύτητας
/// είναι 0=κάτω, 2=αριστερά, 4=πάνω, 6=δεξιά (δεξιόστροφα ανά 45 μοίρες).
/// </summary>
public static class TileCatalog
{
    public const int Cols = 40;
    public const int Rows = 24;

    /// <summary>Ο χαρακτήρας για κενό κελί (γόμα, καθαρισμός).</summary>
    public const char EmptySymbol = '.';

    /// <summary>Ο χαρακτήρας για το εργαλείο «πλαίσιο περιγράμματος».</summary>
    public const char SolidSymbol = '#';

    /// <summary>Ο δείκτης εκκίνησης του παίκτη — το πολύ ΕΝΑΣ ανά δωμάτιο.</summary>
    public const char StartSymbol = '@';

    /// <summary>Ο χαρακτήρας της εξόδου (βλ. <see cref="ExitGraph"/> για την ομαδοποίηση).</summary>
    public const char ExitSymbol = ExitGraph.ExitSymbol;

    /// <summary>Ο χαρακτήρας της τηλεμεταφοράς (βλ. <see cref="TeleportGraph"/>).</summary>
    public const char TeleportSymbol = TeleportGraph.TeleportSymbol;

    private const string GeoGroup = "Geometry";
    private const string SurfaceGroup = "Surfaces & zones";
    private const string HazardGroup = "Hazards";
    private const string ItemGroup = "Items";
    private const string MechGroup = "Mechanisms";

    public static readonly IReadOnlyList<TileType> All =
    [
        // ================= Γεωμετρία =================
        new TileType('.', "empty", GeoGroup, "Empty",
            "Air — the hero passes through freely.",
            "transparent", "transparent",
            // Κενό κελί: δεν ζωγραφίζεται τίποτα, φαίνεται το φόντο του δωματίου.
            ""),

        new TileType('#', "solid", GeoGroup, "Solid",
            "Full 8x8 material — floor, wall or ceiling.",
            Palette.Material, Palette.EdgeColor,
            // Δίτονο πλακίδιο: πορτοκαλί ακμή 1 px γύρω από πράσινο σώμα (concept-art §5).
            """
            <rect x="0" y="0" width="8" height="8" fill="var(--edge)"/>
            <rect x="1" y="1" width="6" height="6" fill="var(--fill)"/>
            """),

        // Τα τρίγωνα βγαίνουν ΑΠΕΥΘΕΙΑΣ από το RAMP_TEST του tools/physics.py,
        // όπου u = στήλη pixel 0..7 και v = γραμμή pixel 0..7 (v προς τα κάτω).
        // Το εξωτερικό πολύγωνο είναι η ακμή, το εσωτερικό (1 μονάδα προς τα μέσα)
        // το σώμα — γι' αυτό οι κορυφές πέφτουν σε 2.414 / 5.586.
        new TileType('/', "ramp_dr", GeoGroup, "Ramp ↗",
            "Solid bottom-right — floor rising to the right (v >= 7-u).",
            Palette.Material, Palette.EdgeColor,
            """
            <polygon points="0,8 8,0 8,8" fill="var(--edge)"/>
            <polygon points="2.414,7 7,2.414 7,7" fill="var(--fill)"/>
            """),

        new TileType('\\', "ramp_dl", GeoGroup, "Ramp ↘",
            "Solid bottom-left — floor dropping to the right (v >= u).",
            Palette.Material, Palette.EdgeColor,
            """
            <polygon points="0,0 0,8 8,8" fill="var(--edge)"/>
            <polygon points="1,2.414 1,7 5.586,7" fill="var(--fill)"/>
            """),

        new TileType('7', "ramp_ur", GeoGroup, "Ceiling ↘",
            "Solid top-right — ceiling dropping to the right (v <= u).",
            Palette.Material, Palette.EdgeColor,
            """
            <polygon points="0,0 8,0 8,8" fill="var(--edge)"/>
            <polygon points="2.414,1 7,1 7,5.586" fill="var(--fill)"/>
            """),

        new TileType('F', "ramp_ul", GeoGroup, "Ceiling ↗",
            "Solid top-left — ceiling rising to the right (v <= 7-u).",
            Palette.Material, Palette.EdgeColor,
            """
            <polygon points="0,0 8,0 0,8" fill="var(--edge)"/>
            <polygon points="1,1 5.586,1 1,5.586" fill="var(--fill)"/>
            """),

        // ================= Κίνδυνοι =================
        // Η φορά είναι αυτή που δείχνουν οι ΜΥΤΕΣ (FACING στο physics.py):
        // ^ πάνω (4), < αριστερά (2), v κάτω (0), > δεξιά (6). Η βάση κάθεται
        // στην αντίθετη πλευρά — από εκεί τα αγγίζεις ακίνδυνα.
        new TileType('^', "spike_u", HazardGroup, "Spikes ↑",
            "Points up, base at the bottom. Solid but deadly from above.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="6" width="8" height="2" fill="var(--fill)"/>
            <polygon points="0,6 1.33,1 2.67,6" fill="var(--edge)"/>
            <polygon points="2.67,6 4,1 5.33,6" fill="var(--edge)"/>
            <polygon points="5.33,6 6.67,1 8,6" fill="var(--edge)"/>
            """),

        new TileType('v', "spike_d", HazardGroup, "Spikes ↓",
            "Points down, base at the top.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="8" height="2" fill="var(--fill)"/>
            <polygon points="0,2 1.33,7 2.67,2" fill="var(--edge)"/>
            <polygon points="2.67,2 4,7 5.33,2" fill="var(--edge)"/>
            <polygon points="5.33,2 6.67,7 8,2" fill="var(--edge)"/>
            """),

        new TileType('<', "spike_l", HazardGroup, "Spikes ←",
            "Points left, base on the right side.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="6" y="0" width="2" height="8" fill="var(--fill)"/>
            <polygon points="6,0 1,1.33 6,2.67" fill="var(--edge)"/>
            <polygon points="6,2.67 1,4 6,5.33" fill="var(--edge)"/>
            <polygon points="6,5.33 1,6.67 6,8" fill="var(--edge)"/>
            """),

        new TileType('>', "spike_r", HazardGroup, "Spikes →",
            "Points right, base on the left side.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="2" height="8" fill="var(--fill)"/>
            <polygon points="2,0 7,1.33 2,2.67" fill="var(--edge)"/>
            <polygon points="2,2.67 7,4 2,5.33" fill="var(--edge)"/>
            <polygon points="2,5.33 7,6.67 2,8" fill="var(--edge)"/>
            """),

        // ================= Επιφάνειες & ζώνες =================
        // Μονόδρομες: η μπάρα κάθεται στην πλευρά από την οποία είναι ΣΤΕΡΕΗ.
        // Τα βελάκια δείχνουν τη φορά που την περνάς.
        new TileType('-', "oneway_u", SurfaceGroup, "One-way ↑",
            "Solid only from above — you pass through it going up from below.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="8" height="2" fill="var(--fill)"/>
            <rect x="0" y="0" width="8" height="0.8" fill="var(--edge)"/>
            <path d="M2,6 L3,4.4 L4,6 M4.6,6 L5.6,4.4 L6.6,6" fill="none"
                  stroke="var(--edge)" stroke-width="0.5"/>
            """),

        new TileType('_', "oneway_d", SurfaceGroup, "One-way ↓",
            "Solid only from below — you pass through it going down from above.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="6" width="8" height="2" fill="var(--fill)"/>
            <rect x="0" y="7.2" width="8" height="0.8" fill="var(--edge)"/>
            <path d="M2,2 L3,3.6 L4,2 M4.6,2 L5.6,3.6 L6.6,2" fill="none"
                  stroke="var(--edge)" stroke-width="0.5"/>
            """),

        new TileType('[', "oneway_l", SurfaceGroup, "One-way ←",
            "Solid only from the left — you pass through it moving left.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="2" height="8" fill="var(--fill)"/>
            <rect x="0" y="0" width="0.8" height="8" fill="var(--edge)"/>
            <path d="M6,2 L4.4,3 L6,4 M6,4.6 L4.4,5.6 L6,6.6" fill="none"
                  stroke="var(--edge)" stroke-width="0.5"/>
            """),

        new TileType(']', "oneway_r", SurfaceGroup, "One-way →",
            "Solid only from the right — you pass through it moving right.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="6" y="0" width="2" height="8" fill="var(--fill)"/>
            <rect x="7.2" y="0" width="0.8" height="8" fill="var(--edge)"/>
            <path d="M2,2 L3.6,3 L2,4 M2,4.6 L3.6,5.6 L2,6.6" fill="none"
                  stroke="var(--edge)" stroke-width="0.5"/>
            """),

        new TileType(':', "gravlock", SurfaceGroup, "Gravity-lock zone",
            "Inside it gravity does NOT change. It is not solid.",
            Palette.Ink, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="8" height="8" fill="var(--fill)" fill-opacity="0.12"/>
            <circle cx="4" cy="4" r="2.4" fill="none" stroke="var(--fill)" stroke-width="0.7"/>
            <line x1="2.3" y1="5.7" x2="5.7" y2="2.3" stroke="var(--fill)" stroke-width="0.7"/>
            """),

        new TileType('%', "crumble", SurfaceGroup, "Fragile",
            "Solid that collapses shortly after you step on it.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="8" height="8" fill="var(--fill)" fill-opacity="0.7"/>
            <path d="M0,2.5 L2,3.5 L1.2,5.5 L2.8,8" fill="none"
                  stroke="var(--edge)" stroke-width="0.6"/>
            <path d="M4.5,0 L4,2.2 L6,3.4 L5.2,5.6 L8,6.6" fill="none"
                  stroke="var(--edge)" stroke-width="0.6"/>
            """),

        // ================= Αντικείμενα =================
        new TileType('X', "exit", ItemGroup, "Exit",
            "The goal of the level.",
            Palette.Ink, Palette.EdgeColor,
            """
            <rect x="0.6" y="0.6" width="6.8" height="6.8" fill="none"
                  stroke="var(--edge)" stroke-width="0.9"/>
            <polygon points="2.6,2.2 5.6,4 2.6,5.8" fill="var(--fill)"/>
            """),

        new TileType('+', "energy", ItemGroup, "Energy",
            "Pickup: +2 energy.",
            Palette.Ink, Palette.EdgeColor,
            """
            <path d="M3.2,1 h1.6 v2.2 h2.2 v1.6 h-2.2 v2.2 h-1.6 v-2.2 h-2.2 v-1.6 h2.2 z"
                  fill="var(--fill)"/>
            """),

        new TileType('P', "parachute", ItemGroup, "Parachute",
            "Pickup: cancels fall damage.",
            Palette.Ink, Palette.EdgeColor,
            """
            <path d="M0.8,4.4 Q4,0.2 7.2,4.4 Z" fill="var(--fill)"/>
            <path d="M0.8,4.4 L4,7.4 M7.2,4.4 L4,7.4 M4,4.4 L4,7.4"
                  fill="none" stroke="var(--fill)" stroke-width="0.4"/>
            """),

        new TileType('k', "key", ItemGroup, "Key",
            "Pickup: opens the lock (K).",
            Palette.Ink, Palette.EdgeColor,
            """
            <circle cx="2.6" cy="3" r="1.4" fill="none" stroke="var(--fill)" stroke-width="0.8"/>
            <path d="M3.6,4 L6.6,6.8 M5,5.4 L4.2,6.3 M5.9,6.2 L5.1,7.1"
                  fill="none" stroke="var(--fill)" stroke-width="0.7"/>
            """),

        new TileType('T', "teleport", ItemGroup, "Teleporter",
            "Sends you to another cell of the SAME room. Set the destination in the \"Teleporters\" panel.",
            Palette.Ink, Palette.EdgeColor,
            """
            <ellipse cx="4" cy="6.3" rx="3" ry="1.2" fill="none"
                     stroke="var(--fill)" stroke-width="0.7"/>
            <ellipse cx="4" cy="2.2" rx="2" ry="0.9" fill="none"
                     stroke="var(--fill)" stroke-width="0.7"/>
            <path d="M1,6.3 L2,2.2 M7,6.3 L6,2.2" fill="none"
                  stroke="var(--fill)" stroke-width="0.5"/>
            """),

        new TileType('B', "crate", ItemGroup, "Crate",
            "Solid that can be pushed and also falls with gravity.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0.6" y="0.6" width="6.8" height="6.8" fill="var(--fill)"/>
            <rect x="0.6" y="0.6" width="6.8" height="6.8" fill="none"
                  stroke="var(--edge)" stroke-width="0.8"/>
            <path d="M0.6,0.6 L7.4,7.4 M7.4,0.6 L0.6,7.4"
                  stroke="var(--edge)" stroke-width="0.6"/>
            """),

        // Δεν είναι αντικείμενο του παιχνιδιού: ο φορτωτής το διαβάζει, το κελί
        // γίνεται κενό και ο παίκτης ξεκινά εκεί. Ένας μόνο ανά δωμάτιο.
        // Κατάσταση εκτέλεσης, όχι εργαλείο σχεδίασης: προκύπτει όταν ο παίκτης
        // ξεκλειδώσει. Υπάρχει εδώ ώστε ο editor να μπορεί να ανοίξει πίστα που
        // αποθηκεύτηκε σε αυτή την κατάσταση.
        new TileType('|', "lock_open", MechGroup, "Lock opened",
            "Unlocked: still visible, but you pass through it.",
            Palette.Material, Palette.EdgeColor,
            """
            <path d="M1.4,3.4 L6.6,3.4 L6.6,7.4 L1.4,7.4 Z" fill="none"
                  stroke="var(--edge)" stroke-width="0.8"/>
            <path d="M2.4,3.4 L2.4,1.6 A1.6,1.6 0 0 1 5.6,1.6" fill="none"
                  stroke="var(--fill)" stroke-width="0.7"
                  transform="rotate(-35 2.4 3.4)"/>
            """),

        // Ίδια λογική με το lock_open: κατάσταση εκτέλεσης, όχι εργαλείο
        // σχεδίασης. Προκύπτει όταν ένας διακόπτης ανοίξει την πόρτα.
        new TileType('g', "gate_open", MechGroup, "Gate opened",
            "Opened by a switch: still visible, but you pass through it.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="1.2" y="0.8" width="5.6" height="6.4" fill="none"
                  stroke="var(--edge)" stroke-width="0.8"
                  stroke-dasharray="1.2 1"/>
            <path d="M4,1.6 L4,6.4" stroke="var(--fill)" stroke-width="0.6"
                  stroke-dasharray="1 1"/>
            """),

        // Κατάσταση εκτέλεσης: προκύπτει όταν αφήσεις κιβώτιο πάνω στην πλάκα.
        new TileType('d', "plate_down", MechGroup, "Plate pressed",
            "A crate is holding this plate down, so its gates stay open.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="1" y="4.4" width="6" height="2.2" fill="var(--fill)"/>
            <rect x="2" y="2.6" width="4" height="1.8" fill="none"
                  stroke="var(--edge)" stroke-width="0.7"/>
            """),

        new TileType('@', "start", MechGroup, "Start position",
            "Where the player starts. The cell stays empty in the game.",
            Palette.Ink, Palette.EdgeColor,
            """
            <circle cx="4" cy="4" r="3" fill="none"
                    stroke="var(--edge)" stroke-width="0.8"/>
            <circle cx="4" cy="2.6" r="0.9" fill="var(--fill)"/>
            <path d="M4,3.6 L4,5.6 M2.8,6.6 L4,5.6 L5.2,6.6 M2.6,4.4 L5.4,4.4"
                  stroke="var(--fill)" stroke-width="0.7" fill="none"/>
            """),

        // ================= Μηχανισμοί =================
        new TileType('K', "lock", MechGroup, "Lock",
            "Solid until you pick up the key (k).",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="8" height="8" fill="var(--fill)"/>
            <circle cx="4" cy="3.2" r="1.1" fill="var(--edge)"/>
            <polygon points="3.3,3.6 4.7,3.6 5.2,6.4 2.8,6.4" fill="var(--edge)"/>
            """),

        new TileType('G', "gate", MechGroup, "Gate",
            "Solid while closed; opened by a switch (S) or a plate (p).",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0" y="0" width="8" height="8" fill="var(--fill)"/>
            <rect x="1" y="0" width="1" height="8" fill="var(--edge)"/>
            <rect x="3.5" y="0" width="1" height="8" fill="var(--edge)"/>
            <rect x="6" y="0" width="1" height="8" fill="var(--edge)"/>
            """),

        new TileType('S', "switch", MechGroup, "Switch",
            "Toggle: permanently flips the state of the gates.",
            Palette.Ink, Palette.EdgeColor,
            """
            <rect x="1" y="6" width="6" height="2" fill="var(--edge)"/>
            <line x1="4" y1="6" x2="6" y2="2.2" stroke="var(--fill)" stroke-width="0.9"/>
            <circle cx="6.1" cy="1.9" r="1" fill="var(--fill)"/>
            """),

        new TileType('p', "plate", MechGroup, "Pressure plate",
            "Active only while pressed by the hero or a crate.",
            Palette.Material, Palette.EdgeColor,
            """
            <rect x="0.6" y="4.8" width="6.8" height="1.4" fill="var(--fill)"/>
            <rect x="1.6" y="6.2" width="1.2" height="1.8" fill="var(--edge)"/>
            <rect x="5.2" y="6.2" width="1.2" height="1.8" fill="var(--edge)"/>
            """),
    ];

    private static readonly Dictionary<char, TileType> BySymbol =
        All.ToDictionary(t => t.Symbol);

    /// <summary>Είναι ο χαρακτήρας έγκυρος τύπος κελιού;</summary>
    public static bool IsValid(char symbol) => BySymbol.ContainsKey(symbol);

    public static TileType? Find(char symbol) =>
        BySymbol.TryGetValue(symbol, out var t) ? t : null;

    /// <summary>Όλοι οι έγκυροι χαρακτήρες, για μηνύματα σφάλματος.</summary>
    public static string ValidSymbols => new(All.Select(t => t.Symbol).ToArray());
}
