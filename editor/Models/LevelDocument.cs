using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace GravassistEditor.Models;

/// <summary>
/// Μια πίστα σε μορφή αρχείου <c>levels/*.txt</c>.
///
/// ΜΟΡΦΗ (πρέπει να μείνει ακριβώς συμβατή με το Room.__init__ του tools/physics.py):
///   - Γραμμή πίστας = ΑΚΡΙΒΩΣ 40 έγκυροι χαρακτήρες. Ο parser της Python κρατάει
///     ΜΟΝΟ αυτές τις γραμμές και απαιτεί να είναι ακριβώς 24.
///   - Οτιδήποτε άλλο αγνοείται· κατά σύμβαση τα σχόλια ξεκινούν με ';'
///     (ΟΧΙ με '#', που είναι στερεό κελί).
///
/// Ό,τι δεν είναι γραμμή πίστας διατηρείται αυτούσιο: οι γραμμές πριν από την πρώτη
/// γραμμή πίστας στο <see cref="Header"/>, οι μετά την τελευταία στο <see cref="Footer"/>.
/// Έτσι τα σχόλια κεφαλής επιβιώνουν σε κάθε αποθήκευση.
///
/// Στην ουρά ζουν και οι ρυθμίσεις («gravity N»), οι συνδέσεις εξόδων
/// («exit &lt;col&gt; &lt;row&gt; &lt;room&gt;» — βλ. <see cref="ExitGraph"/>) και οι
/// τηλεμεταφορές («tp &lt;col&gt; &lt;row&gt; &lt;dcol&gt; &lt;drow&gt;» — βλ.
/// <see cref="TeleportGraph"/>).
/// </summary>
public sealed class LevelDocument
{
    public List<string> Header { get; init; } = [];
    public List<string> Footer { get; init; } = [];

    /// <summary>24 γραμμές των 40 χαρακτήρων.</summary>
    public List<string> Rows { get; init; } = [];

    /// <summary>Είναι η γραμμή έγκυρη γραμμή πίστας (40 έγκυροι χαρακτήρες);</summary>
    public static bool IsGridLine(string line) =>
        line.Length == TileCatalog.Cols && line.All(TileCatalog.IsValid);

    /// <summary>Νέα άδεια πίστα με περίγραμμα από στερεό υλικό και προεπιλεγμένη κεφαλή.</summary>
    public static LevelDocument CreateEmpty(string title = "Νέα πίστα")
    {
        var doc = new LevelDocument
        {
            Header =
            [
                $"; {title} — δωμάτιο {TileCatalog.Cols}x{TileCatalog.Rows}.",
                ";",
                "; ΠΡΟΣΟΧΗ: τα σχόλια ξεκινούν με ';'  (το '#' είναι στερεό κελί).",
                "; Γραμμή πίστας = ΑΚΡΙΒΩΣ 40 έγκυροι χαρακτήρες.",
            ],
        };

        var empty = new string(TileCatalog.EmptySymbol, TileCatalog.Cols);
        var solid = new string(TileCatalog.SolidSymbol, TileCatalog.Cols);
        for (var row = 0; row < TileCatalog.Rows; row++)
        {
            if (row == 0 || row == TileCatalog.Rows - 1)
            {
                doc.Rows.Add(solid);
            }
            else
            {
                var line = new StringBuilder(empty);
                line[0] = TileCatalog.SolidSymbol;
                line[TileCatalog.Cols - 1] = TileCatalog.SolidSymbol;
                doc.Rows.Add(line.ToString());
            }
        }

        return doc;
    }

    /// <summary>
    /// Νέα ΑΙΘΟΥΣΑ: άδειο δωμάτιο με περίγραμμα από στερεό, έναν δείκτη εκκίνησης
    /// '@' μέσα και ουρά «gravity 0». Ό,τι χρειάζεται για να τρέξει αμέσως.
    /// </summary>
    public static LevelDocument CreateRoom(int number)
    {
        var doc = CreateEmpty($"Αίθουσα {number}");
        doc.Header.Insert(1, $"; Αρχείο: {RoomNaming.FileName(number)} — ο αριθμός αίθουσας είναι στο όνομα.");
        doc.Header.Add("; Συνδέσεις εξόδων στην ουρά: exit <col> <row> <room>.");
        doc.Header.Add("; Τηλεμεταφορές στην ουρά: tp <col> <row> <dcol> <drow> (ίδια αίθουσα).");

        // Ο δείκτης εκκίνησης πάει πάνω στο πάτωμα, μέσα από το περίγραμμα.
        var startRow = new StringBuilder(doc.Rows[TileCatalog.Rows - 2]);
        startRow[2] = TileCatalog.StartSymbol;
        doc.Rows[TileCatalog.Rows - 2] = startRow.ToString();

        doc.Footer.Add("gravity 0");
        return doc;
    }

    /// <summary>Διαβάζει το περιεχόμενο ενός αρχείου πίστας.</summary>
    /// <exception cref="LevelFormatException">Αν οι γραμμές πίστας δεν είναι ακριβώς 24.</exception>
    public static LevelDocument Parse(string text)
    {
        var doc = new LevelDocument();
        // Αγνοούμε το τελικό κενό της τελευταίας γραμμής ώστε να μην μπει άδεια γραμμή στο Footer.
        var lines = text.Replace("\r\n", "\n").TrimEnd('\n').Split('\n');

        foreach (var line in lines)
        {
            if (IsGridLine(line))
            {
                doc.Rows.Add(line);
            }
            else if (doc.Rows.Count == 0)
            {
                doc.Header.Add(line);
            }
            else
            {
                doc.Footer.Add(line);
            }
        }

        if (doc.Rows.Count != TileCatalog.Rows)
        {
            throw new LevelFormatException(
                $"Expected {TileCatalog.Rows} level rows of {TileCatalog.Cols} " +
                $"characters, found {doc.Rows.Count}. Valid characters: {TileCatalog.ValidSymbols}");
        }

        return doc;
    }

    /// <summary>
    /// Ελέγχει ότι το έγγραφο θα περάσει από τον parser του physics.py.
    /// Επιστρέφει null αν είναι εντάξει, αλλιώς το ελληνικό μήνυμα σφάλματος.
    /// </summary>
    public string? Validate()
    {
        if (Rows.Count != TileCatalog.Rows)
        {
            return $"The level has {Rows.Count} rows instead of {TileCatalog.Rows}.";
        }

        for (var i = 0; i < Rows.Count; i++)
        {
            var line = Rows[i];
            if (line.Length != TileCatalog.Cols)
            {
                return $"Row {i + 1} has {line.Length} characters instead of {TileCatalog.Cols}.";
            }

            var bad = line.FirstOrDefault(c => !TileCatalog.IsValid(c), '\0');
            if (bad != '\0')
            {
                return $"Unknown character '{bad}' on row {i + 1}. " +
                       $"Valid: {TileCatalog.ValidSymbols}";
            }
        }

        // Σχόλιο που κατά λάθος μοιάζει με γραμμή πίστας θα διαβαστεί ως 25η γραμμή.
        var strays = Header.Concat(Footer).Where(IsGridLine).ToList();
        if (strays.Count > 0)
        {
            return "A comment line looks like a level row — the parser will count it. " +
                   "Start it with ';'.";
        }

        return null;
    }

    // ================= Έξοδοι & αίθουσες =================

    /// <summary>Οι ομάδες γειτονικών κελιών εξόδου, σε σειρά σάρωσης κατά γραμμές.</summary>
    public List<CellGroup> ExitGroups() => ExitGraph.FindGroups(Rows);

    /// <summary>Οι δηλωμένοι προορισμοί («exit …») της ουράς.</summary>
    public List<ExitLink> ExitLinks() => ExitGraph.ParseLines(Footer);

    /// <summary>Οι ομάδες γειτονικών κελιών τηλεμεταφοράς, σε σειρά σάρωσης.</summary>
    public List<CellGroup> TeleportGroups() => TeleportGraph.FindGroups(Rows);

    /// <summary>Οι δηλωμένοι προορισμοί («tp …») της ουράς.</summary>
    public List<TeleportLink> TeleportLinks() => TeleportGraph.ParseLines(Footer);

    /// <summary>Πόσοι δείκτες εκκίνησης '@' υπάρχουν στο πλέγμα.</summary>
    public int StartMarkerCount =>
        Rows.Sum(line => line.Count(c => c == TileCatalog.StartSymbol));

    /// <summary>
    /// Ξαναγράφει τις γραμμές «exit» της ουράς: πετάει τις παλιές και βάζει τις
    /// νέες στο τέλος, μία ανά ομάδα. Ό,τι άλλο υπάρχει στην ουρά (σχόλια,
    /// «gravity N») μένει αυτούσιο και στη σειρά του.
    /// </summary>
    /// <summary>
    /// Αλλάζει τον αριθμό αίθουσας-στόχου σε όσες γραμμές «exit» δείχνουν στο
    /// <paramref name="from"/>, ΕΠΙΤΟΠΟΥ.
    ///
    /// Δεν χρησιμοποιεί το <see cref="SetExitLinks"/> επίτηδες: εκείνο πετάει τις
    /// γραμμές και τις ξαναβάζει στο τέλος, οπότε μια απλή αλλαγή αριθμού θα
    /// αναδιέτασσε την ουρά και θα μόλυνε το diff με ψεύτικες αλλαγές.
    /// </summary>
    /// <returns>Πόσες γραμμές άλλαξαν.</returns>
    public int RenumberExitTargets(int from, int to)
    {
        var changed = 0;
        for (var i = 0; i < Footer.Count; i++)
        {
            var link = ExitGraph.ParseLines([Footer[i]]).FirstOrDefault();
            if (link is null || link.Room != from) continue;
            Footer[i] = ExitGraph.FormatLine(link with { Room = to });
            changed++;
        }

        return changed;
    }

    /// <summary>
    /// Η αρχική φορά βαρύτητας της αίθουσας — η γραμμή «gravity N» της ουράς.
    /// Αν λείπει, ισχύει 0 (DOWN), όπως και στο tools/physics.py.
    /// </summary>
    public int StartGravity
    {
        get
        {
            foreach (var line in Footer)
            {
                var m = GravityPattern.Match(line);
                if (m.Success) return int.Parse(m.Groups[1].Value,
                    CultureInfo.InvariantCulture);
            }

            return 0;
        }
        set
        {
            var g = Math.Clamp(value, 0, 7);
            var line = string.Create(CultureInfo.InvariantCulture, $"gravity {g}");
            // ΕΠΙΤΟΠΟΥ: η γραμμή είναι πάντα πρώτη στην ουρά των υπαρχόντων
            // αρχείων και δεν θέλουμε να τη μετακινήσουμε στο τέλος — θα
            // μόλυνε το diff κάθε φορά που αγγίζεις την αίθουσα.
            for (var i = 0; i < Footer.Count; i++)
            {
                if (!GravityPattern.IsMatch(Footer[i])) continue;
                Footer[i] = line;
                return;
            }

            // Δεν υπήρχε: μπαίνει ΠΡΙΝ από τις «exit»/«tp», για να διαβάζεται
            // η ουρά με την ίδια σειρά παντού.
            var at = Footer.FindIndex(l => ExitGraph.IsExitLine(l)
                                        || TeleportGraph.IsTeleportLine(l));
            if (at < 0) Footer.Add(line); else Footer.Insert(at, line);
        }
    }

    private static readonly Regex GravityPattern =
        new(@"^\s*gravity\s+([0-7])\s*$",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public void SetExitLinks(IEnumerable<ExitLink> links)
    {
        Footer.RemoveAll(ExitGraph.IsExitLine);
        foreach (var link in links) Footer.Add(ExitGraph.FormatLine(link));
    }

    /// <summary>
    /// Ξαναγράφει τις γραμμές «tp» της ουράς, ακριβώς όπως το
    /// <see cref="SetExitLinks"/> κάνει με τις «exit»: πετάει τις παλιές και
    /// βάζει τις νέες στο τέλος, μία ανά ομάδα τηλεμεταφοράς. Σχόλια, «gravity N»
    /// και «exit …» μένουν αυτούσια και στη σειρά τους.
    ///
    /// ΣΕΙΡΑ ΚΛΗΣΗΣ: πρώτα το <see cref="SetExitLinks"/> και μετά αυτό, ώστε η
    /// ουρά να καταλήγει «… exit … / tp …» — η ίδια σειρά με τα υπάρχοντα αρχεία,
    /// άρα η αποθήκευση χωρίς αλλαγές αφήνει το αρχείο ταυτόσημο.
    /// </summary>
    public void SetTeleportLinks(IEnumerable<TeleportLink> links)
    {
        Footer.RemoveAll(TeleportGraph.IsTeleportLine);
        foreach (var link in links) Footer.Add(TeleportGraph.FormatLine(link));
    }

    /// <summary>Οι δηλώσεις καλωδίωσης της ουράς.</summary>
    public List<AttrLink> AttrLinks() => AttrGraph.ParseLines(Footer);

    /// <summary>Οι ομάδες κελιών ενός είδους καλωδίωσης.</summary>
    public List<CellGroup> AttrGroups(string kind) =>
        AttrGraph.FindGroups(Rows, kind);

    /// <summary>
    /// Ξαναγράφει τις γραμμές καλωδίωσης. Ό,τι έχει τιμή 0 ΔΕΝ γράφεται: το 0
    /// είναι η προεπιλογή και μια γραμμή για αυτό είναι σκέτος θόρυβος στο
    /// αρχείο και στο diff.
    /// </summary>
    public void SetAttrLinks(IEnumerable<AttrLink> links)
    {
        Footer.RemoveAll(AttrGraph.IsAttrLine);
        foreach (var link in links.Where(l => l.Value != 0))
            Footer.Add(AttrGraph.FormatLine(link));
    }

    /// <summary>
    /// Επικύρωση περιεχομένου (πέρα από τη μορφή): δείκτες εκκίνησης και έξοδοι.
    ///
    /// <paramref name="roomExists"/> απαντά αν υπάρχει αρχείο για μια αίθουσα.
    /// Ο ανύπαρκτος προορισμός είναι ΠΡΟΕΙΔΟΠΟΙΗΣΗ, όχι σφάλμα: ο χρήστης
    /// μπορεί κάλλιστα να φτιάξει την αίθουσα αργότερα.
    /// </summary>
    public ValidationReport ValidateContent(Func<int, bool> roomExists)
    {
        var errors = new List<string>();
        var warnings = new List<string>();

        var starts = StartMarkerCount;
        if (starts > 1)
        {
            errors.Add($"There are {starts} start markers '@' — at most one is allowed.");
        }
        else if (starts == 0)
        {
            warnings.Add("There is no start marker '@' — the player will start at the default position.");
        }

        var groups = ExitGroups();
        var byAnchor = ExitLinks()
            .GroupBy(l => (l.Col, l.Row))
            .ToDictionary(g => g.Key, g => g.Last().Room);

        foreach (var group in groups)
        {
            var where = $"col {group.Col}, row {group.Row}";
            var size = group.Cells.Count == 1 ? "1 cell" : $"{group.Cells.Count} cells";
            if (!byAnchor.TryGetValue((group.Col, group.Row), out var room))
            {
                errors.Add($"The exit at {where} ({size}) has no declared destination.");
                continue;
            }

            if (!roomExists(room))
            {
                warnings.Add($"The exit at {where} leads to room {room}, " +
                             $"which does not exist yet as file {RoomNaming.FileName(room)}.");
            }
        }

        // Δηλώσεις που δείχνουν σε θέση χωρίς ομάδα εξόδου: ορφανές, θα χαθούν.
        var anchors = groups.Select(g => (g.Col, g.Row)).ToHashSet();
        foreach (var link in ExitLinks().Where(l => !anchors.Contains((l.Col, l.Row))))
        {
            warnings.Add($"The declaration \"{ExitGraph.FormatLine(link)}\" does not match " +
                         "an exit group on the grid and was ignored.");
        }

        ValidateTeleports(errors, warnings);
        return new ValidationReport(errors, warnings);
    }

    /// <summary>
    /// Επικύρωση των τηλεμεταφορών.
    ///
    /// Ομάδα χωρίς προορισμό = ΠΡΟΕΙΔΟΠΟΙΗΣΗ: στο physics.py ο προορισμός μένει
    /// None και η τηλεμεταφορά απλώς δεν κάνει τίποτα — ο χρήστης μπορεί να τη
    /// συμπληρώσει αργότερα. Προορισμός εκτός πλέγματος = ΣΦΑΛΜΑ: θα έστελνε τον
    /// παίκτη έξω από το δωμάτιο.
    /// </summary>
    private void ValidateTeleports(List<string> errors, List<string> warnings)
    {
        var groups = TeleportGroups();
        var links = TeleportLinks();
        var byAnchor = links
            .GroupBy(l => (l.Col, l.Row))
            .ToDictionary(g => g.Key, g => g.Last());

        foreach (var group in groups)
        {
            var where = $"col {group.Col}, row {group.Row}";
            var size = group.Cells.Count == 1 ? "1 cell" : $"{group.Cells.Count} cells";
            if (!byAnchor.TryGetValue((group.Col, group.Row), out var link))
            {
                warnings.Add($"The teleporter at {where} ({size}) has no declared " +
                             "destination and will do nothing in the game.");
                continue;
            }

            if (link.DestCol < 0 || link.DestCol >= TileCatalog.Cols ||
                link.DestRow < 0 || link.DestRow >= TileCatalog.Rows)
            {
                errors.Add($"The teleporter at {where} points to cell " +
                           $"({link.DestCol},{link.DestRow}), outside the grid " +
                           $"0..{TileCatalog.Cols - 1} x 0..{TileCatalog.Rows - 1}.");
            }
        }

        // Δηλώσεις που δείχνουν σε θέση χωρίς ομάδα τηλεμεταφοράς: ορφανές.
        var anchors = groups.Select(g => (g.Col, g.Row)).ToHashSet();
        foreach (var link in links.Where(l => !anchors.Contains((l.Col, l.Row))))
        {
            warnings.Add($"The declaration \"{TeleportGraph.FormatLine(link)}\" does not match " +
                         "a teleporter group on the grid and was ignored.");
        }
    }

    /// <summary>Παράγει το κείμενο του αρχείου (κεφαλή + 24 γραμμές + ουρά, LF, τελικό newline).</summary>
    public string Serialize()
    {
        var sb = new StringBuilder();
        foreach (var line in Header) sb.Append(line).Append('\n');
        foreach (var line in Rows) sb.Append(line).Append('\n');
        foreach (var line in Footer) sb.Append(line).Append('\n');
        return sb.ToString();
    }
}

/// <summary>Σφάλμα μορφής αρχείου πίστας.</summary>
public sealed class LevelFormatException(string message) : Exception(message);

/// <summary>
/// Αποτέλεσμα επικύρωσης: τα σφάλματα εμποδίζουν την αποθήκευση, οι
/// προειδοποιήσεις απλώς εμφανίζονται στον χρήστη.
/// </summary>
public sealed record ValidationReport(
    IReadOnlyList<string> Errors,
    IReadOnlyList<string> Warnings)
{
    public bool Ok => Errors.Count == 0;
}
