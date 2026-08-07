using GravassistEditor.Models;

namespace GravassistEditor.Services;

/// <summary>
/// Πρόσβαση στον φάκελο <c>levels/</c> του repo.
///
/// Ο φάκελος βρίσκεται από τη ρύθμιση "LevelsPath" του appsettings.json· αν είναι
/// σχετική διαδρομή, ερμηνεύεται ως προς τη ρίζα του project (editor/). Προεπιλογή
/// "../levels", δηλαδή ο φάκελος πιστών του repo.
/// </summary>
public sealed class LevelStore
{
    private const string Extension = ".txt";

    public string RootPath { get; }

    public LevelStore(IConfiguration config, IWebHostEnvironment env)
    {
        var configured = config["LevelsPath"];
        if (string.IsNullOrWhiteSpace(configured)) configured = "../levels";

        RootPath = Path.GetFullPath(Path.IsPathRooted(configured)
            ? configured
            : Path.Combine(env.ContentRootPath, configured));
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
            throw new LevelFormatException("Λείπει το όνομα αρχείου.");
        }

        name = name.Trim();
        if (!name.EndsWith(Extension, StringComparison.OrdinalIgnoreCase)) name += Extension;

        // Μόνο σκέτο όνομα αρχείου: κανένα '/', '\' ή '..'.
        if (name != Path.GetFileName(name) || name.Contains(".."))
        {
            throw new LevelFormatException($"Μη αποδεκτό όνομα αρχείου: {name}");
        }

        var full = Path.GetFullPath(Path.Combine(RootPath, name));
        if (!full.StartsWith(RootPath + Path.DirectorySeparatorChar, StringComparison.Ordinal))
        {
            throw new LevelFormatException($"Μη αποδεκτό όνομα αρχείου: {name}");
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
