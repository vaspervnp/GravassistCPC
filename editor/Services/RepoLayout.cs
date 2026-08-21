namespace GravassistEditor.Services;

/// <summary>
/// Πού είναι η ρίζα του repo — τα <c>tools/</c>, το <c>Makefile</c>, τα
/// <c>levels/</c>.
///
/// ΓΙΑΤΙ ΥΠΑΡΧΕΙ: ο editor υπολόγιζε τη ρίζα ως «ο τρέχων κατάλογος συν
/// <c>..</c>». Αυτό ισχύει ΜΟΝΟ όταν τρέχεις <c>dotnet run</c> μέσα από το
/// <c>editor/</c>. Σε πραγματικό deployment η διεργασία ξεκινά από αλλού
/// (<c>bin/Debug/net10.0</c>, ένα systemd unit, ένας φάκελος publish) και η
/// ρίζα έβγαινε λάθος — το «Build .dsk» έψαχνε το <c>tools/genasm.py</c> μέσα
/// στο <c>bin/</c> και το ίδιο θα συνέβαινε και με τα <c>levels/</c>.
///
/// Η ΛΥΣΗ ΔΕΝ ΕΙΝΑΙ ΑΛΛΟ ΕΝΑ ΣΧΕΤΙΚΟ ΜΟΝΟΠΑΤΙ, είναι να ΨΑΞΟΥΜΕ: ανεβαίνουμε
/// από τον φάκελο της εφαρμογής μέχρι να βρούμε κατάλογο που όντως περιέχει
/// αυτά που χρειαζόμαστε. Και αν κάποιος έχει ασυνήθιστη διάταξη, το
/// <c>RepoPath</c> στο appsettings (ή η μεταβλητή <c>gravassistRepo</c>) το
/// λέει ρητά.
/// </summary>
public sealed class RepoLayout
{
    public const string PathKey = "RepoPath";
    public const string PathVar = "gravassistRepo";

    /// <summary>
    /// Πού είναι το <c>wwwroot</c> — ΨΑΧΝΟΝΤΑΣ, όπως και η ρίζα του repo.
    ///
    /// ΤΟ BUILD OUTPUT ΔΕΝ ΤΟ ΑΝΤΙΓΡΑΦΕΙ: τα static web assets λύνονται από
    /// manifest που δείχνει στις πηγές, και το content root είναι ο κατάλογος
    /// από τον οποίο ξεκίνησε η διεργασία. Τρέχοντας το DLL από αλλού, ή με
    /// <c>--contentRoot</c>, το wwwroot δεν βρίσκεται και ΚΑΘΕ στατικό αρχείο
    /// γυρνά 404 — ενώ ο editor φαίνεται μια χαρά, γιατί οι σελίδες του είναι
    /// μεταγλωττισμένες μέσα στο DLL. Το test run πέθαινε ακριβώς έτσι, με
    /// σκέτο «HTTP ERROR 404» και κανένα άλλο σημάδι.
    ///
    /// Το σημάδι είναι το <c>game/play.html</c>: αν λείπει, ο φάκελος μπορεί
    /// να λέγεται wwwroot αλλά δεν είναι ο δικός μας.
    /// </summary>
    public static string? FindWebRoot(params string?[] starts)
    {
        foreach (var start in starts)
        {
            if (string.IsNullOrWhiteSpace(start)) continue;
            for (var d = new DirectoryInfo(Path.GetFullPath(start));
                 d is not null; d = d.Parent)
                foreach (var cand in new[] { Path.Combine(d.FullName, "wwwroot"),
                                             Path.Combine(d.FullName, "editor", "wwwroot") })
                    if (File.Exists(Path.Combine(cand, "game", "play.html")))
                        return cand;
        }
        return null;
    }

    /// <summary>Τα σημάδια ότι βρήκαμε τη ρίζα: αυτά ακριβώς θέλει το χτίσιμο.</summary>
    private static readonly string[] Markers = ["Makefile", "tools/genasm.py"];

    /// <summary>Η ρίζα του repo· <c>null</c> αν δεν βρέθηκε.</summary>
    public string? RepoRoot { get; }

    /// <summary>Ο κοινός φάκελος πιστών, γονέας των προσωπικών φακέλων.</summary>
    public string LevelsRoot { get; }

    public RepoLayout(IWebHostEnvironment env, IConfiguration config, ILogger<RepoLayout> log)
    {
        var told = Blank(config[PathVar]) ?? Blank(config[PathKey]);
        if (told is not null)
        {
            RepoRoot = Absolute(told, env.ContentRootPath);
            if (!Looks(RepoRoot))
                log.LogWarning("Το {Key}={Path} δεν μοιάζει με ρίζα του repo "
                               + "(λείπει {Markers}). Το χτίσιμο θα αποτύχει.",
                               PathKey, RepoRoot, string.Join(" / ", Markers));
        }
        else
        {
            // Δύο αφετηρίες: ο content root (συνήθως το editor/) και ο φάκελος
            // του ίδιου του assembly. Σε deployment οι δύο διαφέρουν, και δεν
            // υπάρχει λόγος να μαντέψουμε ποιος είναι ο σωστός.
            RepoRoot = Find(env.ContentRootPath) ?? Find(AppContext.BaseDirectory);
            if (RepoRoot is null)
                log.LogError("Δεν βρέθηκε η ρίζα του repo ψάχνοντας προς τα πάνω "
                             + "από {Content} και {Base}. Όρισε το {Key} στο "
                             + "appsettings.json ή τη μεταβλητή {Var}. Χωρίς αυτό "
                             + "το «Build .dsk» δεν δουλεύει.",
                             env.ContentRootPath, AppContext.BaseDirectory,
                             PathKey, PathVar);
        }

        // Τα levels ακολουθούν τη ρίζα, εκτός αν έχουν οριστεί ρητά.
        var levels = Blank(config["LevelsPath"]);
        LevelsRoot = levels is not null
            ? Absolute(levels, env.ContentRootPath)
            : Path.Combine(RepoRoot ?? env.ContentRootPath, "levels");

        log.LogInformation("Ρίζα repo: {Root}   Πίστες: {Levels}",
                           RepoRoot ?? "(δεν βρέθηκε)", LevelsRoot);
    }

    /// <summary>
    /// Ανεβαίνει από τον <paramref name="start"/> ώσπου να βρει κατάλογο που
    /// περιέχει ΟΛΑ τα σημάδια. Επιστρέφει <c>null</c> αν φτάσει στη ρίζα του
    /// δίσκου χωρίς να τα βρει.
    /// </summary>
    public static string? Find(string? start)
    {
        if (string.IsNullOrWhiteSpace(start)) return null;
        var dir = new DirectoryInfo(Path.GetFullPath(start));
        while (dir is not null)
        {
            if (Looks(dir.FullName)) return dir.FullName;
            dir = dir.Parent;
        }

        return null;
    }

    /// <summary>Μοιάζει αυτός ο κατάλογος με ρίζα του repo;</summary>
    public static bool Looks(string dir) =>
        Markers.All(m => File.Exists(Path.Combine(dir, m.Replace('/', Path.DirectorySeparatorChar))));

    private static string Absolute(string path, string relativeTo)
    {
        path = Environment.ExpandEnvironmentVariables(path);
        return Path.GetFullPath(Path.IsPathRooted(path)
            ? path
            : Path.Combine(relativeTo, path));
    }

    private static string? Blank(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
