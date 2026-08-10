using System.Text.RegularExpressions;
using GravassistEditor.Models;

namespace GravassistEditor.Services;

/// <summary>
/// Έλεγχος στην εκκίνηση: ο κατάλογος <see cref="TileCatalog"/> πρέπει να έχει τους
/// ΙΔΙΟΥΣ χαρακτήρες με το CHARS του tools/physics.py.
///
/// Ο βασικός developer προσθέτει τύπους κελιών στο physics.py· χωρίς αυτόν τον έλεγχο
/// η απόκλιση θα φαινόταν μόνο ως «άγνωστος χαρακτήρας» τη στιγμή που θα άνοιγε μια
/// πίστα. Ο έλεγχος είναι ΜΟΝΟ προειδοποίηση στο log — δεν σταματάει τον editor.
/// </summary>
public static partial class PhysicsCharsCheck
{
    [GeneratedRegex(@"CHARS\s*=\s*\{(.*?)\}", RegexOptions.Singleline)]
    private static partial Regex CharsBlock();

    // Δέχεται "." : EMPTY και "\\": RAMP_DL — μας ενδιαφέρει μόνο το κλειδί.
    [GeneratedRegex("\"((?:\\\\.|[^\"\\\\])+)\"\\s*:")]
    private static partial Regex CharKey();

    /// <summary>Διαβάζει τους χαρακτήρες του CHARS· null αν το αρχείο δεν βρέθηκε/διαβάστηκε.</summary>
    public static HashSet<char>? ReadSymbols(string physicsPath)
    {
        if (!File.Exists(physicsPath)) return null;

        string source;
        try
        {
            source = File.ReadAllText(physicsPath);
        }
        catch (IOException)
        {
            return null;
        }

        var block = CharsBlock().Match(source);
        if (!block.Success) return null;

        var symbols = new HashSet<char>();
        foreach (Match m in CharKey().Matches(block.Groups[1].Value))
        {
            // Το μόνο escape που εμφανίζεται στο physics.py είναι το "\\" (backslash).
            var key = m.Groups[1].Value.Replace("\\\\", "\\");
            if (key.Length == 1) symbols.Add(key[0]);
        }

        return symbols.Count > 0 ? symbols : null;
    }

    /// <summary>Τρέχει τον έλεγχο και γράφει το αποτέλεσμα στο log.</summary>
    public static void Run(string physicsPath, ILogger logger)
    {
        var fromPhysics = ReadSymbols(physicsPath);
        if (fromPhysics is null)
        {
            logger.LogInformation(
                "Could not read CHARS from {Path} — the cell-type agreement check is skipped.",
                physicsPath);
            return;
        }

        var fromCatalog = TileCatalog.All.Select(t => t.Symbol).ToHashSet();

        var missing = new string(fromPhysics.Except(fromCatalog).Order().ToArray());
        var extra = new string(fromCatalog.Except(fromPhysics).Order().ToArray());

        if (missing.Length == 0 && extra.Length == 0)
        {
            logger.LogInformation(
                "The {Count} cell types agree with CHARS in physics.py.", fromCatalog.Count);
            return;
        }

        if (missing.Length > 0)
        {
            logger.LogWarning(
                "Types present in physics.py but MISSING from the editor: {Symbols}. " +
                "Add them to Models/TileType.cs (TileCatalog.All).", missing);
        }

        if (extra.Length > 0)
        {
            logger.LogWarning(
                "Types present in the editor but NOT in physics.py: {Symbols}. " +
                "The Python parser will reject levels that use them.", extra);
        }
    }
}
