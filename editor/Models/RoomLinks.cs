using System.Globalization;
using System.Text.RegularExpressions;

namespace GravassistEditor.Models;

/// <summary>Ένα κελί του πλέγματος (στήλη, γραμμή).</summary>
public sealed record GridCell(int Col, int Row);

/// <summary>
/// Μία ΟΜΑΔΑ γειτονικών κελιών του ίδιου χαρακτήρα — δηλαδή ΕΝΑ αντικείμενο.
///
/// Γειτνίαση 4 (πάνω/κάτω/αριστερά/δεξιά): όσα κελιά αγγίζονται αποτελούν το ίδιο
/// αντικείμενο (μία έξοδος, μία τηλεμεταφορά) και οδηγούν αναγκαστικά στον ίδιο
/// προορισμό. Η ομάδα ταυτοποιείται από το πάνω-αριστερό της κελί
/// (<see cref="Col"/>, <see cref="Row"/>) με σάρωση κατά γραμμές: μικρότερο row,
/// μετά μικρότερο col.
/// </summary>
public sealed record CellGroup(int Col, int Row, IReadOnlyList<GridCell> Cells);

/// <summary>
/// Μία γραμμή footer «exit &lt;col&gt; &lt;row&gt; &lt;room&gt; [διπλή] [acol] [arow]».
/// </summary>
/// <param name="TwoWay">
/// Διπλής κατεύθυνσης: η αίθουσα προορισμού έχει πόρτα που γυρίζει εδώ, οπότε
/// ο παίκτης δεν ξεκινά από το σημείο εκκίνησης όταν επιστρέφει.
/// </param>
/// <param name="ArriveCol">
/// Πού εμφανίζεται ο παίκτης ΒΓΑΙΝΟΝΤΑΣ από αυτή την πόρτα. Ανήκει στην πόρτα
/// και όχι στην αίθουσα, γιατί κάθε πόρτα βγάζει αλλού. null = να το βρει μόνο
/// του το παιχνίδι (πρώτο ελεύθερο διπλανό κελί)· αυτό αρκεί μόνο όταν η πόρτα
/// δεν είναι κολλημένη σε γωνία ή σε άλλη πόρτα, γι' αυτό και ορίζεται ρητά.
/// </param>
/// <param name="ArriveG">
/// Φορά βαρύτητας (0..7) με την οποία μπαίνει ο παίκτης. null = η αρχική φορά
/// της αίθουσας — που είναι λάθος όποτε η πόρτα βρίσκεται σε τοίχο ή σε
/// ταβάνι, γιατί η αίθουσα «ξεκινάει» αλλού από εκεί που μπαίνεις.
/// </param>
public sealed record ExitLink(int Col, int Row, int Room, bool TwoWay = false,
    int? ArriveCol = null, int? ArriveRow = null, int? ArriveG = null);

/// <summary>
/// Μία γραμμή footer «tp &lt;col&gt; &lt;row&gt; &lt;dcol&gt; &lt;drow&gt;».
/// Το (Col,Row) είναι το πάνω-αριστερό κελί της ομάδας τηλεμεταφοράς και το
/// (DestCol,DestRow) το κελί της ΙΔΙΑΣ αίθουσας όπου βγαίνει ο παίκτης.
/// </summary>
public sealed record TeleportLink(int Col, int Row, int DestCol, int DestRow);

/// <summary>
/// Μία γραμμή footer «sw|gate|lock|key &lt;col&gt; &lt;row&gt; &lt;τιμή&gt;».
///
/// Ο σύνδεσμος ΔΕΝ είναι κελί αλλά ΑΡΙΘΜΟΣ: «κανάλι» για διακόπτες και πόρτες,
/// «ταυτότητα» για κλειδιά και κλειδαριές. Γι' αυτό ένας διακόπτης μπορεί να
/// οδηγεί όσες πόρτες θέλει ο σχεδιαστής, όπου κι αν βρίσκονται.
/// </summary>
public sealed record AttrLink(string Kind, int Col, int Row, int Value);

/// <summary>
/// Ανάγνωση και γραφή των γραμμών καλωδίωσης του footer.
///
/// Ένας πίνακας για τα τέσσερα είδη: κάθε κελί έχει ακριβώς έναν τύπο, οπότε
/// το είδος προκύπτει από το ίδιο το πλέγμα και δεν υπάρχει ασάφεια.
/// </summary>
public static class AttrGraph
{
    /// <summary>Χαρακτήρας πλέγματος ανά είδος καλωδίωσης.</summary>
    public static readonly (string Kind, char[] Symbols)[] Kinds =
    [
        // Κάθε όψη και κάθε κατάσταση: ο σχεδιαστής μπορεί να ζωγραφίσει τον
        // διακόπτη ήδη πατημένο, όπως και την ανοιγμένη πύλη.
        ("sw", ['S', 'Q', 'A', 'E', 's', 'q', 'a', 'e']),
        ("plate", ['p', 'd']),       // 'd' = πατημένη, με κιβώτιο από πάνω
        ("gate", ['G', 'g']),        // 'g' = ανοιγμένη· κρατά την καλωδίωσή της
        ("lock", ['K', '|']),
        ("key", ['k']),
        // Τα αγκάθια τραβιούνται μέσα όπως ανοίγει μια πύλη. Και οι οκτώ
        // μορφές (τέσσερις φορές x βγαλμένα/τραβηγμένα) είναι ΕΝΑ είδος:
        // η φορά ζει στον τύπο του κελιού, όχι στην καλωδίωση.
        ("spikes", ['^', 'v', '<', '>', 'u', 'j', 'h', 'l']),
    ];

    private static readonly Regex LinePattern = new(
        @"^\s*(sw|gate|lock|key|plate|spikes)\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static bool IsAttrLine(string line) => LinePattern.IsMatch(line);

    public static string FormatLine(AttrLink link) => string.Create(
        CultureInfo.InvariantCulture,
        $"{link.Kind} {link.Col} {link.Row} {link.Value}");

    public static List<AttrLink> ParseLines(IEnumerable<string> lines)
    {
        var links = new List<AttrLink>();
        foreach (var line in lines)
        {
            var m = LinePattern.Match(line);
            if (!m.Success) continue;
            links.Add(new AttrLink(
                m.Groups[1].Value.ToLowerInvariant(),
                int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[4].Value, CultureInfo.InvariantCulture)));
        }

        return links;
    }

    /// <summary>Οι ομάδες κελιών ενός είδους, σε σειρά σάρωσης κατά γραμμές.</summary>
    public static List<CellGroup> FindGroups(IReadOnlyList<string> rows, string kind)
    {
        var symbols = Kinds.First(k => k.Kind == kind).Symbols;
        var groups = symbols.SelectMany(s => CellGroups.Find(rows, s)).ToList();
        groups.Sort((a, b) => a.Row != b.Row ? a.Row - b.Row : a.Col - b.Col);
        return groups;
    }
}

/// <summary>
/// Ομαδοποίηση γειτονικών κελιών ενός χαρακτήρα (γειτνίαση 4).
///
/// Είναι η ίδια πλημμύρα με το <c>Room._groups_of</c> του tools/physics.py —
/// αν αλλάξει εκεί ο κανόνας, πρέπει να αλλάξει κι εδώ.
/// </summary>
public static class CellGroups
{
    /// <summary>
    /// Βρίσκει τις ομάδες κελιών με χαρακτήρα <paramref name="symbol"/>.
    ///
    /// Σάρωση κατά γραμμές· το πρώτο κελί που συναντάμε σε κάθε συνεκτική
    /// συνιστώσα είναι εξ ορισμού το πάνω-αριστερό της, άρα γίνεται το
    /// αναγνωριστικό της ομάδας. Οι ομάδες επιστρέφονται με τη σειρά σάρωσης.
    /// </summary>
    public static List<CellGroup> Find(IReadOnlyList<string> rows, char symbol)
    {
        var groups = new List<CellGroup>();
        if (rows.Count == 0) return groups;

        var seen = new HashSet<(int Row, int Col)>();
        for (var row = 0; row < rows.Count; row++)
        {
            var line = rows[row];
            for (var col = 0; col < line.Length; col++)
            {
                if (line[col] != symbol || !seen.Add((row, col))) continue;

                // Πλημμύρα σε γειτνίαση 4 από το πάνω-αριστερό κελί της ομάδας.
                var cells = new List<GridCell>();
                var stack = new Stack<(int Row, int Col)>();
                stack.Push((row, col));
                while (stack.Count > 0)
                {
                    var (r, c) = stack.Pop();
                    cells.Add(new GridCell(c, r));
                    foreach (var (nr, nc) in new[] { (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1) })
                    {
                        if (nr < 0 || nr >= rows.Count) continue;
                        if (nc < 0 || nc >= rows[nr].Length) continue;
                        if (rows[nr][nc] != symbol) continue;
                        if (!seen.Add((nr, nc))) continue;
                        stack.Push((nr, nc));
                    }
                }

                // Σταθερή σειρά κελιών (row-major) ώστε το JSON να μην αλλάζει τυχαία.
                cells.Sort((a, b) => a.Row != b.Row ? a.Row - b.Row : a.Col - b.Col);
                groups.Add(new CellGroup(col, row, cells));
            }
        }

        return groups;
    }
}

/// <summary>
/// Ομαδοποίηση των κελιών εξόδου και ανάγνωση/γραφή των γραμμών «exit» του footer.
///
/// Η γραμμή footer έχει τη μορφή:
///   exit &lt;col&gt; &lt;row&gt; &lt;room&gt;
/// όπου (col,row) είναι το ΠΑΝΩ-ΑΡΙΣΤΕΡΟ κελί της ομάδας και room ο αριθμός της
/// αίθουσας προορισμού (αρχείο <c>levels/room_&lt;room&gt;.txt</c>).
/// Μία γραμμή ανά ομάδα εξόδου.
///
/// Ο parser του tools/physics.py αγνοεί ό,τι δεν είναι γραμμή πίστας, οπότε οι
/// γραμμές αυτές είναι ασφαλείς για την υπάρχουσα μορφή αρχείου.
/// </summary>
public static class ExitGraph
{
    /// <summary>Ο χαρακτήρας της εξόδου στο πλέγμα.</summary>
    public const char ExitSymbol = 'X';

    // Χαλαρό ταίριασμα (κενά, πεζά/κεφαλαία) ώστε να διαβάζονται και γραμμές
    // γραμμένες στο χέρι.
    // Τα προαιρετικά πεδία είναι ΘΕΣΗΣ: το σημείο άφιξης έρχεται μετά τη σημαία
    // διπλής κατεύθυνσης, οπότε για να γράψεις άφιξη πρέπει να γράψεις και σημαία.
    private static readonly Regex LinePattern = new(
        @"^\s*exit\s+(\d+)\s+(\d+)\s+(\d+)"
        + @"(?:\s+([01])(?:\s+(\d+)\s+(\d+)(?:\s+([0-7]))?)?)?\s*$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Είναι η γραμμή δήλωση εξόδου (και όχι σχόλιο ή ρύθμιση);</summary>
    public static bool IsExitLine(string line) => LinePattern.IsMatch(line);

    /// <summary>Η γραμμή footer για έναν σύνδεσμο εξόδου.</summary>
    public static string FormatLine(ExitLink link)
    {
        var head = string.Create(CultureInfo.InvariantCulture,
            $"exit {link.Col} {link.Row} {link.Room}");
        if (link.ArriveCol is { } ac && link.ArriveRow is { } ar)
        {
            var body = string.Create(CultureInfo.InvariantCulture,
                $"{head} {(link.TwoWay ? 1 : 0)} {ac} {ar}");
            return link.ArriveG is { } ag
                ? string.Create(CultureInfo.InvariantCulture, $"{body} {ag}")
                : body;
        }
        return link.TwoWay ? head + " 1" : head;
    }

    /// <summary>Οι δηλώσεις «exit» μιας ουράς αρχείου, με τη σειρά που εμφανίζονται.</summary>
    public static List<ExitLink> ParseLines(IEnumerable<string> lines)
    {
        var links = new List<ExitLink>();
        foreach (var line in lines)
        {
            var m = LinePattern.Match(line);
            if (!m.Success) continue;
            links.Add(new ExitLink(
                int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture),
                m.Groups[4].Success && m.Groups[4].Value == "1",
                m.Groups[5].Success
                    ? int.Parse(m.Groups[5].Value, CultureInfo.InvariantCulture) : null,
                m.Groups[6].Success
                    ? int.Parse(m.Groups[6].Value, CultureInfo.InvariantCulture) : null,
                m.Groups[7].Success
                    ? int.Parse(m.Groups[7].Value, CultureInfo.InvariantCulture) : null));
        }

        return links;
    }

    /// <summary>Οι ομάδες κελιών εξόδου, σε σειρά σάρωσης κατά γραμμές.</summary>
    public static List<CellGroup> FindGroups(IReadOnlyList<string> rows) =>
        CellGroups.Find(rows, ExitSymbol);
}

/// <summary>
/// Ομαδοποίηση των κελιών τηλεμεταφοράς και ανάγνωση/γραφή των γραμμών «tp».
///
/// Η γραμμή footer έχει τη μορφή:
///   tp &lt;col&gt; &lt;row&gt; &lt;dcol&gt; &lt;drow&gt;
/// όπου (col,row) είναι το ΠΑΝΩ-ΑΡΙΣΤΕΡΟ κελί της ομάδας τηλεμεταφοράς και
/// (dcol,drow) το κελί της ΙΔΙΑΣ αίθουσας όπου βγαίνει ο παίκτης.
/// Μία γραμμή ανά ομάδα τηλεμεταφοράς.
///
/// Αδήλωτη τηλεμεταφορά δεν κάνει τίποτα στο παιχνίδι (βλ. Room._link του
/// tools/physics.py: ο προορισμός μένει None), γι' αυτό είναι ΠΡΟΕΙΔΟΠΟΙΗΣΗ και
/// όχι σφάλμα.
/// </summary>
public static class TeleportGraph
{
    /// <summary>Ο χαρακτήρας της τηλεμεταφοράς στο πλέγμα.</summary>
    public const char TeleportSymbol = 'T';

    private static readonly Regex LinePattern = new(
        @"^\s*tp\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Είναι η γραμμή δήλωση τηλεμεταφοράς;</summary>
    public static bool IsTeleportLine(string line) => LinePattern.IsMatch(line);

    /// <summary>Η γραμμή footer για μία τηλεμεταφορά.</summary>
    public static string FormatLine(TeleportLink link) => string.Create(
        CultureInfo.InvariantCulture,
        $"tp {link.Col} {link.Row} {link.DestCol} {link.DestRow}");

    /// <summary>Οι δηλώσεις «tp» μιας ουράς αρχείου, με τη σειρά που εμφανίζονται.</summary>
    public static List<TeleportLink> ParseLines(IEnumerable<string> lines)
    {
        var links = new List<TeleportLink>();
        foreach (var line in lines)
        {
            var m = LinePattern.Match(line);
            if (!m.Success) continue;
            links.Add(new TeleportLink(
                int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture),
                int.Parse(m.Groups[4].Value, CultureInfo.InvariantCulture)));
        }

        return links;
    }

    /// <summary>Οι ομάδες κελιών τηλεμεταφοράς, σε σειρά σάρωσης κατά γραμμές.</summary>
    public static List<CellGroup> FindGroups(IReadOnlyList<string> rows) =>
        CellGroups.Find(rows, TeleportSymbol);
}

/// <summary>
/// Ονοματοδοσία αιθουσών: τα αρχεία αίθουσας λέγονται <c>room_&lt;N&gt;.txt</c>,
/// όπου N ακέραιος. Ο αριθμός της αίθουσας ζει ΜΕΣΑ στο όνομα του αρχείου —
/// δεν υπάρχει άλλο μητρώο.
/// </summary>
public static class RoomNaming
{
    /// <summary>
    /// Ο προορισμός που σημαίνει «εδώ τελειώνει το παιχνίδι» — δες
    /// <c>ROOM_END</c> στο src/endings.asm. ΟΧΙ 0: το 0 σημαίνει ήδη
    /// «πόρτα χωρίς δηλωμένο προορισμό».
    /// </summary>
    public const int EndOfGame = 255;

    private static readonly Regex NamePattern = new(
        @"^room_(\d+)\.txt$", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Ο αριθμός αίθουσας ενός ονόματος αρχείου, ή null αν δεν είναι αίθουσα.</summary>
    public static int? NumberOf(string fileName)
    {
        var m = NamePattern.Match(fileName);
        return m.Success && int.TryParse(m.Groups[1].Value, NumberStyles.None,
            CultureInfo.InvariantCulture, out var n) ? n : null;
    }

    /// <summary>Το όνομα αρχείου μιας αίθουσας.</summary>
    public static string FileName(int number) =>
        string.Create(CultureInfo.InvariantCulture, $"room_{number}.txt");
}
