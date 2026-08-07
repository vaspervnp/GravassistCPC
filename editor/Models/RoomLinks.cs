using System.Globalization;
using System.Text.RegularExpressions;

namespace GravassistEditor.Models;

/// <summary>Ένα κελί του πλέγματος (στήλη, γραμμή).</summary>
public sealed record ExitCell(int Col, int Row);

/// <summary>
/// Μία ΟΜΑΔΑ γειτονικών κελιών εξόδου — δηλαδή μία έξοδος.
///
/// Γειτνίαση 4 (πάνω/κάτω/αριστερά/δεξιά): όσα κελιά 'X' αγγίζονται αποτελούν
/// την ίδια έξοδο και οδηγούν αναγκαστικά στην ίδια αίθουσα. Η ομάδα
/// ταυτοποιείται από το πάνω-αριστερό της κελί (<see cref="Col"/>,
/// <see cref="Row"/>) με σάρωση κατά γραμμές: μικρότερο row, μετά μικρότερο col.
/// </summary>
public sealed record ExitGroup(int Col, int Row, IReadOnlyList<ExitCell> Cells);

/// <summary>Μία γραμμή footer «exit &lt;col&gt; &lt;row&gt; &lt;room&gt;».</summary>
public sealed record ExitLink(int Col, int Row, int Room);

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
    private static readonly Regex LinePattern = new(
        @"^\s*exit\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Είναι η γραμμή δήλωση εξόδου (και όχι σχόλιο ή ρύθμιση);</summary>
    public static bool IsExitLine(string line) => LinePattern.IsMatch(line);

    /// <summary>Η γραμμή footer για έναν σύνδεσμο εξόδου.</summary>
    public static string FormatLine(ExitLink link) =>
        string.Create(CultureInfo.InvariantCulture, $"exit {link.Col} {link.Row} {link.Room}");

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
                int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture)));
        }

        return links;
    }

    /// <summary>
    /// Βρίσκει τις ομάδες εξόδου του πλέγματος.
    ///
    /// Σάρωση κατά γραμμές· το πρώτο κελί που συναντάμε σε κάθε συνεκτική
    /// συνιστώσα είναι εξ ορισμού το πάνω-αριστερό της, άρα γίνεται το
    /// αναγνωριστικό της ομάδας. Οι ομάδες επιστρέφονται με τη σειρά σάρωσης.
    /// </summary>
    public static List<ExitGroup> FindGroups(IReadOnlyList<string> rows)
    {
        var groups = new List<ExitGroup>();
        if (rows.Count == 0) return groups;

        var seen = new HashSet<(int Row, int Col)>();
        for (var row = 0; row < rows.Count; row++)
        {
            var line = rows[row];
            for (var col = 0; col < line.Length; col++)
            {
                if (line[col] != ExitSymbol || !seen.Add((row, col))) continue;

                // Πλημμύρα σε γειτνίαση 4 από το πάνω-αριστερό κελί της ομάδας.
                var cells = new List<ExitCell>();
                var stack = new Stack<(int Row, int Col)>();
                stack.Push((row, col));
                while (stack.Count > 0)
                {
                    var (r, c) = stack.Pop();
                    cells.Add(new ExitCell(c, r));
                    foreach (var (nr, nc) in new[] { (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1) })
                    {
                        if (nr < 0 || nr >= rows.Count) continue;
                        if (nc < 0 || nc >= rows[nr].Length) continue;
                        if (rows[nr][nc] != ExitSymbol) continue;
                        if (!seen.Add((nr, nc))) continue;
                        stack.Push((nr, nc));
                    }
                }

                // Σταθερή σειρά κελιών (row-major) ώστε το JSON να μην αλλάζει τυχαία.
                cells.Sort((a, b) => a.Row != b.Row ? a.Row - b.Row : a.Col - b.Col);
                groups.Add(new ExitGroup(col, row, cells));
            }
        }

        return groups;
    }
}

/// <summary>
/// Ονοματοδοσία αιθουσών: τα αρχεία αίθουσας λέγονται <c>room_&lt;N&gt;.txt</c>,
/// όπου N ακέραιος. Ο αριθμός της αίθουσας ζει ΜΕΣΑ στο όνομα του αρχείου —
/// δεν υπάρχει άλλο μητρώο.
/// </summary>
public static class RoomNaming
{
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
