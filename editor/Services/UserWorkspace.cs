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
public sealed class UserWorkspace(RepoLayout layout)
{
    /// <summary>
    /// Η ρίζα με τα κοινά αρχεία — και ο γονέας των προσωπικών φακέλων.
    /// Έρχεται από το <see cref="RepoLayout"/>: ήταν «content root + ../levels»,
    /// που σε deployment έδειχνε μέσα στο bin/.
    /// </summary>
    public string SharedRoot { get; } = layout.LevelsRoot;

    /// <summary>
    /// Η διαδρομή κάτω από τη ρίζα των πιστών, με το όνομά της μπροστά:
    /// <c>/levels/kapoios_at_example.com</c>. Αν για οποιονδήποτε λόγο η ρίζα
    /// δεν είναι πρόγονος, γυρνά το όνομα του φακέλου σκέτο — ποτέ ολόκληρη
    /// την απόλυτη διαδρομή.
    /// </summary>
    public string Display(string path)
    {
        var root = Path.GetFullPath(SharedRoot).TrimEnd(Path.DirectorySeparatorChar);
        var full = Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
        var name = "/" + (Path.GetFileName(root) is { Length: > 0 } n ? n : "levels");
        if (string.Equals(full, root, StringComparison.Ordinal)) return name;
        if (!full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            return name + "/" + Path.GetFileName(full);
        return name + "/" + full[(root.Length + 1)..]
            .Replace(Path.DirectorySeparatorChar, '/');
    }

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
    /// Καλείται ΜΙΑ φορά, τη στιγμή της σύνδεσης, για λογαριασμούς που
    /// δημοσιεύουν: ο φάκελός τους ευθυγραμμίζεται με τα κοινά <c>levels/</c>.
    ///
    /// Γιατί μόνο γι' αυτούς: δουλεύουν πάνω στο κοινό σύνολο και το γράφουν
    /// πίσω· αν ξεκινούσαν από ένα παλιό αντίγραφο, το επόμενο «Publish» θα
    /// γύριζε πίσω τη δουλειά κάποιου άλλου. Οι υπόλοιποι κρατούν το δικό τους
    /// αντίγραφο και δεν πρέπει να τους το πατήσει τίποτα.
    ///
    /// Γιατί στη σύνδεση και όχι σε κάθε αίτημα: το τράβηγμα ΠΑΤΑΕΙ αρχεία.
    /// Στη μέση της δουλειάς θα έσβηνε ό,τι έχεις σώσει και δεν έχεις
    /// δημοσιεύσει, χωρίς να το ζητήσεις.
    /// </summary>
    /// <returns>Τα ονόματα που ενημερώθηκαν.</returns>
    public List<string> SyncOnSignIn(ClaimsPrincipal user) => Pull(PathFor(user));

    /// <summary>
    /// Ποια αρχεία του χρήστη διαφέρουν από τα κοινά — δηλαδή τι ΘΑ άλλαζε μια
    /// δημοσίευση. Δεν γράφει τίποτα.
    ///
    /// Γιατί χωριστά από τη <see cref="Publish"/>: η δημοσίευση πατά πάνω στα
    /// αρχεία που βλέπουν όλοι. Ο χρήστης πρέπει να δει ΟΝΟΜΑΣΤΙΚΑ τι θα
    /// αλλάξει πριν το κάνει, όχι μετά.
    /// </summary>
    /// <returns>Ζεύγη (όνομα αρχείου, «new» ή «changed»).</returns>
    public List<(string Name, string Kind)> PublishPreview(string userDir) =>
        Diff(userDir, SharedRoot);

    /// <summary>Τι θα άλλαζε ένα τράβηγμα των κοινών προς τον χρήστη.</summary>
    public List<(string Name, string Kind)> PullPreview(string userDir) =>
        Diff(SharedRoot, userDir);

    /// <summary>
    /// Αντιγράφει τα <c>*.txt</c> του χρήστη πάνω στα κοινά.
    ///
    /// ΜΟΝΟ .txt: η δισκέτα του χρήστη και οτιδήποτε άλλο μένει στον φάκελό
    /// του. ΔΕΝ ΣΒΗΝΕΙ ΠΟΤΕ κοινό αρχείο — αν ο χρήστης διέγραψε μια αίθουσα
    /// τοπικά, η κοινή μένει· η διαγραφή της δουλειάς κάποιου άλλου δεν πρέπει
    /// να είναι παρενέργεια ενός κουμπιού «δημοσίευση».
    /// </summary>
    /// <returns>Τα ονόματα που όντως γράφτηκαν.</returns>
    public List<string> Publish(string userDir) => Copy(userDir, SharedRoot);

    /// <summary>
    /// Το αντίστροφο: φέρνει τα κοινά <c>*.txt</c> στον φάκελο του χρήστη.
    ///
    /// ΠΑΤΑΕΙ τα δικά του αρχεία όπου διαφέρουν — αυτό είναι το νόημα: ο
    /// λογαριασμός που δημοσιεύει δουλεύει πάνω στο κοινό σύνολο, δεν κρατά
    /// δικό του κλάδο. Ό,τι έχει σώσει και ΔΕΝ έχει δημοσιεύσει χάνεται, γι'
    /// αυτό ο editor δείχνει ονομαστικά τι θα αντικατασταθεί πριν το κάνει.
    /// Αρχεία που υπάρχουν μόνο σ' αυτόν ΔΕΝ σβήνονται.
    /// </summary>
    public List<string> Pull(string userDir) => Copy(SharedRoot, userDir);

    private static List<(string Name, string Kind)> Diff(string from, string to)
    {
        var list = new List<(string, string)>();
        if (!Directory.Exists(from)) return list;
        foreach (var src in Directory.EnumerateFiles(from, "*.txt").OrderBy(p => p))
        {
            var name = Path.GetFileName(src);
            var dst = Path.Combine(to, name);
            if (!File.Exists(dst)) list.Add((name, "new"));
            else if (!SameBytes(src, dst)) list.Add((name, "changed"));
        }

        return list;
    }

    private static List<string> Copy(string from, string to)
    {
        var done = new List<string>();
        foreach (var (name, _) in Diff(from, to))
        {
            File.Copy(Path.Combine(from, name), Path.Combine(to, name), overwrite: true);
            done.Add(name);
        }

        return done;
    }

    private static bool SameBytes(string a, string b)
    {
        var fa = new FileInfo(a);
        var fb = new FileInfo(b);
        if (fa.Length != fb.Length) return false;
        return File.ReadAllBytes(a).AsSpan().SequenceEqual(File.ReadAllBytes(b));
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
