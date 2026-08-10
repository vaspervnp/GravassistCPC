using System.Security.Claims;
using System.Text;

namespace GravassistEditor.Services;

/// <summary>
/// Ο προσωπικός φάκελος πιστών κάθε χρήστη: <c>levels/&lt;λογαριασμός&gt;/</c>.
///
/// ΤΗΝ ΠΡΩΤΗ ΦΟΡΑ αντιγράφονται εκεί όσα αρχεία υπάρχουν στο <c>levels/</c>,
/// ώστε να ξεκινάς με τις υπάρχουσες αίθουσες αντί για άδειο φάκελο. Από κει
/// και πέρα ο κάθε λογαριασμός δουλεύει στα δικά του.
///
/// ΤΟ ΟΝΟΜΑ ΤΟΥ ΦΑΚΕΛΟΥ ΒΓΑΙΝΕΙ ΑΠΟ ΤΟ EMAIL, καθαρισμένο. Ο έλεγχος δεν
/// είναι φιλολογικός: ένα «..» ή ένα «/» μέσα σε claim θα έγραφε έξω από το
/// levels/, οπότε κρατάμε ΜΟΝΟ ασφαλείς χαρακτήρες και επαληθεύουμε στο τέλος
/// ότι η διαδρομή που φτιάχτηκε είναι όντως μέσα στη ρίζα.
/// </summary>
public sealed class UserWorkspace(IWebHostEnvironment env, IConfiguration config)
{
    /// <summary>Η ρίζα με τα κοινά αρχεία — και ο γονέας των προσωπικών φακέλων.</summary>
    public string SharedRoot { get; } = Path.GetFullPath(
        Path.IsPathRooted(config["LevelsPath"] ?? "../levels")
            ? config["LevelsPath"] ?? "../levels"
            : Path.Combine(env.ContentRootPath, config["LevelsPath"] ?? "../levels"));

    /// <summary>
    /// Μετατρέπει έναν λογαριασμό σε ασφαλές όνομα φακέλου.
    /// Κρατά μόνο γράμματα, ψηφία, τελεία, παύλα και κάτω παύλα.
    /// </summary>
    public static string KeyFor(ClaimsPrincipal user)
    {
        var raw = user.FindFirstValue(ClaimTypes.Email)
                  ?? user.FindFirstValue(ClaimTypes.NameIdentifier)
                  ?? "";
        var sb = new StringBuilder(raw.Length);
        foreach (var c in raw.ToLowerInvariant())
        {
            if (char.IsAsciiLetterOrDigit(c) || c is '.' or '-' or '_') sb.Append(c);
            else if (c == '@') sb.Append("_at_");
        }

        var key = sb.ToString().Trim('.');
        return key.Length == 0 ? "unknown" : key;
    }

    /// <summary>
    /// Ο φάκελος του χρήστη· τον φτιάχνει και τον σπέρνει την πρώτη φορά.
    /// </summary>
    public string PathFor(ClaimsPrincipal user)
    {
        var key = KeyFor(user);
        var dir = Path.GetFullPath(Path.Combine(SharedRoot, key));

        // ΔΙΚΛΕΙΔΑ: ό,τι κι αν βγήκε από τα claims, η διαδρομή πρέπει να είναι
        // ΜΕΣΑ στη ρίζα. Ο καθαρισμός από πάνω το εγγυάται ήδη, αλλά ο έλεγχος
        // κοστίζει τίποτα και πιάνει μελλοντική αλλαγή στο KeyFor.
        var root = SharedRoot.TrimEnd(Path.DirectorySeparatorChar);
        if (!dir.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            throw new InvalidOperationException($"Μη έγκυρος φάκελος χρήστη: {key}");

        if (!Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
            Seed(dir);
        }

        return dir;
    }

    /// <summary>
    /// Αντιγράφει τα κοινά αρχεία στον νέο φάκελο. Μόνο ΑΡΧΕΙΑ της ρίζας —
    /// οι φάκελοι των άλλων χρηστών δεν αντιγράφονται ποτέ.
    /// </summary>
    private void Seed(string dir)
    {
        if (!Directory.Exists(SharedRoot)) return;
        foreach (var src in Directory.EnumerateFiles(SharedRoot, "*.txt"))
        {
            var name = Path.GetFileName(src);
            File.Copy(src, Path.Combine(dir, name), overwrite: false);
        }
    }
}
