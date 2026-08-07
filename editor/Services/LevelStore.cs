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

    /// <summary>Τα ονόματα των αρχείων πίστας, αλφαβητικά.</summary>
    public IReadOnlyList<string> List()
    {
        if (!Directory.Exists(RootPath)) return [];
        return Directory.EnumerateFiles(RootPath, "*" + Extension)
            .Select(Path.GetFileName)
            .Where(n => n is not null)
            .Select(n => n!)
            .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

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

    /// <summary>Αποθηκεύει την πίστα· επικυρώνει πρώτα ώστε να μη γραφτεί άκυρο αρχείο.</summary>
    /// <exception cref="LevelFormatException">Αν η πίστα δεν είναι έγκυρη.</exception>
    public void Save(string name, LevelDocument doc)
    {
        var error = doc.Validate();
        if (error is not null) throw new LevelFormatException(error);

        var path = ResolvePath(name);
        Directory.CreateDirectory(RootPath);
        File.WriteAllText(path, doc.Serialize());
    }
}
