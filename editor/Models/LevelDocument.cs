using System.Text;

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
                $"Περίμενα {TileCatalog.Rows} γραμμές πίστας των {TileCatalog.Cols} " +
                $"χαρακτήρων, βρήκα {doc.Rows.Count}. Έγκυροι χαρακτήρες: {TileCatalog.ValidSymbols}");
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
            return $"Η πίστα έχει {Rows.Count} γραμμές αντί για {TileCatalog.Rows}.";
        }

        for (var i = 0; i < Rows.Count; i++)
        {
            var line = Rows[i];
            if (line.Length != TileCatalog.Cols)
            {
                return $"Η γραμμή {i + 1} έχει {line.Length} χαρακτήρες αντί για {TileCatalog.Cols}.";
            }

            var bad = line.FirstOrDefault(c => !TileCatalog.IsValid(c), '\0');
            if (bad != '\0')
            {
                return $"Άγνωστος χαρακτήρας '{bad}' στη γραμμή {i + 1}. " +
                       $"Έγκυροι: {TileCatalog.ValidSymbols}";
            }
        }

        // Σχόλιο που κατά λάθος μοιάζει με γραμμή πίστας θα διαβαστεί ως 25η γραμμή.
        var strays = Header.Concat(Footer).Where(IsGridLine).ToList();
        if (strays.Count > 0)
        {
            return "Γραμμή σχολίου μοιάζει με γραμμή πίστας — ο parser θα τη μετρήσει. " +
                   "Ξεκίνησέ την με ';'.";
        }

        return null;
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
