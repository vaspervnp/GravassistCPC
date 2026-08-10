using GravassistEditor.Models;

namespace GravassistEditor.Services;

/// <summary>
/// Πρόσβαση στις πίστες ΤΟΥ ΣΥΝΔΕΔΕΜΕΝΟΥ ΧΡΗΣΤΗ.
///
/// Η ρίζα δεν είναι πια το κοινό <c>levels/</c> αλλά ο προσωπικός υποφάκελός
/// του (<see cref="UserWorkspace"/>). Το αντικείμενο είναι scoped ανά αίτημα:
/// singleton θα κλείδωνε τον πρώτο χρήστη που θα συνδεόταν και όλοι οι
/// υπόλοιποι θα έγραφαν στα δικά του αρχεία.
/// </summary>
public sealed class LevelStore
{
    private const string Extension = ".txt";

    public string RootPath { get; }

    public LevelStore(UserWorkspace workspace, IHttpContextAccessor http)
    {
        var user = http.HttpContext?.User
            ?? throw new InvalidOperationException("Χωρίς αίτημα δεν υπάρχει χρήστης.");
        RootPath = workspace.PathFor(user);
    }

    /// <summary>
    /// Τα αρχεία πίστας: πρώτα οι ΑΙΘΟΥΣΕΣ (room_&lt;N&gt;.txt) ταξινομημένες
    /// ΑΡΙΘΜΗΤΙΚΑ — ώστε το room_2 να έρχεται πριν το room_10, όχι μετά — και
    /// μετά τα υπόλοιπα αρχεία αλφαβητικά.
    /// </summary>
    public IReadOnlyList<LevelFileInfo> List()
    {
        if (!Directory.Exists(RootPath)) return [];

        var files = Directory.EnumerateFiles(RootPath, "*" + Extension)
            .Select(Path.GetFileName)
            .Where(n => n is not null)
            .Select(n => new LevelFileInfo(n!, RoomNaming.NumberOf(n!)))
            .ToList();

        return files
            .OrderBy(f => f.Room is null)
            .ThenBy(f => f.Room ?? 0)
            .ThenBy(f => f.Name, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    /// <summary>Ο μικρότερος ΕΛΕΥΘΕΡΟΣ αριθμός αίθουσας, ξεκινώντας από το 1.</summary>
    public int NextRoomNumber()
    {
        var used = List().Select(f => f.Room).Where(n => n is not null).Select(n => n!.Value).ToHashSet();
        var n = 1;
        while (used.Contains(n)) n++;
        return n;
    }

    /// <summary>Υπάρχει αρχείο για την αίθουσα με αυτόν τον αριθμό;</summary>
    public bool RoomExists(int number) => File.Exists(ResolvePath(RoomNaming.FileName(number)));

    /// <summary>
    /// Μετατρέπει όνομα αρχείου σε πλήρη διαδρομή μέσα στον φάκελο πιστών.
    /// Απορρίπτει διαδρομές (path traversal) και επιβάλλει την κατάληξη .txt.
    /// </summary>
    /// <exception cref="LevelFormatException">Αν το όνομα δεν είναι αποδεκτό.</exception>
    public string ResolvePath(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
        {
            throw new LevelFormatException("Missing file name.");
        }

        name = name.Trim();
        if (!name.EndsWith(Extension, StringComparison.OrdinalIgnoreCase)) name += Extension;

        // Μόνο σκέτο όνομα αρχείου: κανένα '/', '\' ή '..'.
        if (name != Path.GetFileName(name) || name.Contains(".."))
        {
            throw new LevelFormatException($"Invalid file name: {name}");
        }

        var full = Path.GetFullPath(Path.Combine(RootPath, name));
        if (!full.StartsWith(RootPath + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        {
            throw new LevelFormatException($"Invalid file name: {name}");
        }

        return full;
    }

    public bool Exists(string name) => File.Exists(ResolvePath(name));

    public LevelDocument Load(string name) => LevelDocument.Parse(File.ReadAllText(ResolvePath(name)));

    /// <summary>
    /// Αποθηκεύει την πίστα· επικυρώνει πρώτα ώστε να μη γραφτεί άκυρο αρχείο.
    /// Επιστρέφει τις προειδοποιήσεις (π.χ. προορισμός σε αίθουσα που δεν υπάρχει
    /// ακόμα) — αυτές ΔΕΝ εμποδίζουν την εγγραφή.
    /// </summary>
    /// <exception cref="LevelFormatException">Αν η πίστα δεν είναι έγκυρη.</exception>
    public IReadOnlyList<string> Save(string name, LevelDocument doc)
    {
        var error = doc.Validate();
        if (error is not null) throw new LevelFormatException(error);

        var report = doc.ValidateContent(RoomExists);
        if (!report.Ok) throw new LevelFormatException(string.Join(" ", report.Errors));

        var path = ResolvePath(name);
        Directory.CreateDirectory(RootPath);
        File.WriteAllText(path, doc.Serialize());
        return report.Warnings;
    }

    /// <summary>
    /// Δημιουργεί ΝΕΑ ΑΙΘΟΥΣΑ με τον επόμενο ελεύθερο αριθμό και τη γράφει στον δίσκο.
    /// Επιστρέφει τον αριθμό και το έγγραφο, ώστε ο editor να την ανοίξει αμέσως.
    /// </summary>
    /// <summary>
    /// Αντιγράφει αίθουσα στον επόμενο ελεύθερο αριθμό.
    ///
    /// Το αντίγραφο κρατά τις εξόδους και τις τηλεμεταφορές του πρωτοτύπου: οι
    /// έξοδοι δείχνουν σε ΑΛΛΕΣ αίθουσες και παραμένουν έγκυρες. Κανείς όμως δεν
    /// δείχνει στο αντίγραφο — αυτό το συνδέεις εσύ.
    /// </summary>
    public (int Number, string Name, LevelDocument Doc) CopyRoom(int from)
    {
        var src = RoomNaming.FileName(from);
        if (!Exists(src))
            throw new LevelFormatException($"Room {from} does not exist.");

        var number = NextRoomNumber();
        var name = RoomNaming.FileName(number);
        File.Copy(ResolvePath(src), ResolvePath(name));
        return (number, name, Load(name));
    }

    /// <summary>
    /// Μετακινεί αίθουσα σε άλλον αριθμό και ΕΝΗΜΕΡΩΝΕΙ ΟΛΕΣ τις αναφορές.
    ///
    /// Αυτό είναι το ουσιώδες: ο αριθμός της αίθουσας ζει και μέσα στις γραμμές
    /// «exit … &lt;room&gt;» των ΑΛΛΩΝ αιθουσών. Σκέτη μετονομασία αρχείου θα άφηνε
    /// πόρτες να δείχνουν σε αίθουσα που δεν υπάρχει — και θα το ανακάλυπτες
    /// παίζοντας, όχι σχεδιάζοντας.
    /// </summary>
    /// <returns>Πόσες αναφορές ενημερώθηκαν, ανά αρχείο.</returns>
    public IReadOnlyList<string> MoveRoom(int from, int to)
    {
        if (from == to) return Array.Empty<string>();
        if (!RoomExists(from))
            throw new LevelFormatException($"Room {from} does not exist.");
        if (RoomExists(to))
            throw new LevelFormatException(
                $"Room {to} already exists. Pick a free number, or move that one first.");

        var touched = new List<string>();
        var oldName = RoomNaming.FileName(from);
        var newName = RoomNaming.FileName(to);
        File.Move(ResolvePath(oldName), ResolvePath(newName));
        touched.Add($"{oldName} → {newName}");

        foreach (var info in List())
        {
            var doc = Load(info.Name);
            var n = doc.RenumberExitTargets(from, to);
            if (n == 0) continue;

            File.WriteAllText(ResolvePath(info.Name), doc.Serialize());
            touched.Add($"{info.Name}: {n} " + (n == 1 ? "exit" : "exits"));
        }

        return touched;
    }

    public (int Number, string Name, LevelDocument Doc) CreateRoom()
    {
        Directory.CreateDirectory(RootPath);
        var number = NextRoomNumber();
        var name = RoomNaming.FileName(number);
        var doc = LevelDocument.CreateRoom(number);
        File.WriteAllText(ResolvePath(name), doc.Serialize());
        return (number, name, doc);
    }
}
