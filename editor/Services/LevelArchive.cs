using System.IO.Compression;
using GravassistEditor.Models;

namespace GravassistEditor.Services;

/// <summary>Τι θα άλλαζε μια εισαγωγή σε ένα αρχείο.</summary>
/// <param name="Name">Το όνομα όπως θα γραφτεί — ΠΑΝΤΑ σκέτο όνομα.</param>
/// <param name="Kind">«new», «changed», «same», «skipped» ή «error».</param>
/// <param name="Detail">Γιατί, όταν δεν είναι προφανές.</param>
public sealed record ImportEntry(string Name, string Kind, string Detail = "");

/// <summary>
/// Εξαγωγή και εισαγωγή ΟΛΩΝ των πιστών ως ένα .zip.
///
/// ΓΙΑΤΙ ΥΠΑΡΧΕΙ: ένας φάκελος ανά λογαριασμό σημαίνει ότι η δουλειά σου δεν
/// βγαίνει από εκεί χωρίς πρόσβαση στον δίσκο του server. Το zip είναι ο
/// τρόπος να την πάρεις μαζί σου, να τη δώσεις σε άλλον, ή να τη γυρίσεις
/// πίσω μετά από πείραμα.
///
/// ΤΟ ZIP ΕΙΝΑΙ ΞΕΝΟ ΑΡΧΕΙΟ και το μεταχειριζόμαστε ανάλογα:
///
///   - Τα ονόματα κόβονται σε ΣΚΕΤΟ όνομα αρχείου. Χωρίς αυτό, μια εγγραφή
///     «../../etc/cron.d/x» γράφει έξω από τον φάκελο του χρήστη — η κλασική
///     ευπάθεια «zip slip», και εδώ θα ήταν εκτέλεση κώδικα.
///   - Μόνο .txt. Ό,τι άλλο αγνοείται, δεν απορρίπτει το zip.
///   - Όρια σε πλήθος και μέγεθος, ώστε ένα «zip bomb» να μη γεμίσει τον δίσκο.
///   - ΚΑΘΕ πίστα επικυρώνεται ΠΡΙΝ γραφτεί ΟΤΙΔΗΠΟΤΕ. Μισή εισαγωγή είναι
///     χειρότερη από καμία: μένεις με μερικά δωμάτια νέα και μερικά παλιά,
///     και οι πόρτες δείχνουν σε λάθος μέρη.
/// </summary>
public sealed class LevelArchive
{
    public const int MaxEntries = 400;
    public const int MaxEntryBytes = 64 * 1024;      // μια πίστα είναι ~1.5 KB
    public const long MaxTotalBytes = 4 * 1024 * 1024;

    /// <summary>Όλα τα <c>*.txt</c> του φακέλου σε ένα zip, στη μνήμη.</summary>
    public byte[] Export(string dir)
    {
        using var ms = new MemoryStream();
        // ΠΡΟΣΟΧΗ στο leaveOpen: χωρίς αυτό το ZipArchive κλείνει το
        // MemoryStream και το ToArray() γυρίζει άδειο buffer.
        using (var zip = new ZipArchive(ms, ZipArchiveMode.Create, leaveOpen: true))
        {
            foreach (var path in Directory.EnumerateFiles(dir, "*.txt")
                                          .OrderBy(p => p, StringComparer.Ordinal))
            {
                var entry = zip.CreateEntry(Path.GetFileName(path),
                                            CompressionLevel.Optimal);
                using var to = entry.Open();
                using var from = File.OpenRead(path);
                from.CopyTo(to);
            }
        }

        return ms.ToArray();
    }

    /// <summary>
    /// Διαβάζει το zip και λέει τι ΘΑ γινόταν. Δεν γράφει τίποτα.
    /// Το ίδιο μονοπάτι με την πραγματική εισαγωγή, ώστε η προεπισκόπηση να
    /// μη λέει άλλα από ό,τι κάνει το κουμπί.
    /// </summary>
    public List<ImportEntry> Plan(Stream zipStream, string dir) =>
        Read(zipStream, dir).Plan;

    /// <summary>
    /// Γράφει τα αρχεία. Αν ΕΣΤΩ ΕΝΑ είναι άκυρο, δεν γράφεται κανένα.
    /// </summary>
    /// <returns>Το ίδιο σχέδιο, με τα «new»/«changed» να έχουν γραφτεί.</returns>
    public List<ImportEntry> Import(Stream zipStream, string dir)
    {
        var (plan, bodies) = Read(zipStream, dir);
        if (plan.Any(e => e.Kind == "error")) return plan;

        foreach (var e in plan.Where(e => e.Kind is "new" or "changed"))
            File.WriteAllText(Path.Combine(dir, e.Name), bodies[e.Name]);
        return plan;
    }

    private (List<ImportEntry> Plan, Dictionary<string, string> Bodies)
        Read(Stream zipStream, string dir)
    {
        var plan = new List<ImportEntry>();
        var bodies = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        ZipArchive zip;
        try
        {
            zip = new ZipArchive(zipStream, ZipArchiveMode.Read);
        }
        catch (InvalidDataException)
        {
            plan.Add(new ImportEntry("(zip)", "error", "This is not a readable .zip file."));
            return (plan, bodies);
        }

        using (zip)
        {
            long total = 0;
            var seen = 0;
            foreach (var entry in zip.Entries)
            {
                if (entry.FullName.EndsWith('/')) continue;     // φάκελος
                if (++seen > MaxEntries)
                {
                    plan.Add(new ImportEntry("(zip)", "error",
                        $"More than {MaxEntries} files in the archive."));
                    break;
                }

                // ΜΟΝΟ ΤΟ ΟΝΟΜΑ. Ό,τι διαδρομή κι αν κουβαλά η εγγραφή,
                // πέφτει εδώ: αυτό κόβει το «zip slip».
                var name = Path.GetFileName(entry.FullName);
                if (!name.EndsWith(".txt", StringComparison.OrdinalIgnoreCase))
                {
                    plan.Add(new ImportEntry(name, "skipped", "not a .txt file"));
                    continue;
                }

                if (name != entry.FullName)
                {
                    plan.Add(new ImportEntry(name, "skipped",
                        $"the archive stores it under a path ({entry.FullName})"));
                    continue;
                }

                if (entry.Length > MaxEntryBytes)
                {
                    plan.Add(new ImportEntry(name, "error",
                        $"{entry.Length} bytes — a level is about 1.5 KB."));
                    continue;
                }

                string text;
                using (var reader = new StreamReader(entry.Open()))
                    text = reader.ReadToEnd();

                total += text.Length;
                if (total > MaxTotalBytes)
                {
                    plan.Add(new ImportEntry("(zip)", "error",
                        "The archive is far larger than a set of levels."));
                    break;
                }

                // Η ΙΔΙΑ ΕΠΙΚΥΡΩΣΗ με το κουμπί Save. Ένα zip από αλλού μπορεί
                // να έχει ό,τι να 'ναι μέσα, και ένα μισοσπασμένο δωμάτιο θα
                // έριχνε τον parser του παιχνιδιού πολύ αργότερα.
                try
                {
                    var doc = LevelDocument.Parse(text);
                    if (doc.Validate() is { } problem)
                    {
                        plan.Add(new ImportEntry(name, "error", problem));
                        continue;
                    }
                }
                catch (LevelFormatException ex)
                {
                    plan.Add(new ImportEntry(name, "error", ex.Message));
                    continue;
                }

                bodies[name] = text;
                var dest = Path.Combine(dir, name);
                plan.Add(new ImportEntry(name,
                    !File.Exists(dest) ? "new"
                    : File.ReadAllText(dest) == text ? "same" : "changed"));
            }
        }

        if (plan.Count == 0)
            plan.Add(new ImportEntry("(zip)", "error", "No .txt files in the archive."));
        return (plan, bodies);
    }
}
