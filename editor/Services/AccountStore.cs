using System.Text.Json;

namespace GravassistEditor.Services;

/// <summary>Ένας λογαριασμός και η κατάστασή του.</summary>
/// <param name="Email">Πεζά, όπως τα δίνει η Google.</param>
/// <param name="Allowed">Εγκεκριμένος; Αλλιώς περιμένει έγκριση.</param>
/// <param name="Note">«invited» ή «asked» — πώς μπήκε στη λίστα.</param>
public sealed record Account(string Email, bool Allowed, string Note, DateTime Seen);

/// <summary>
/// Ποιοι λογαριασμοί επιτρέπονται.
///
/// ΜΕΧΡΙ ΝΑ ΕΓΚΡΙΘΕΙ, ΚΑΝΕΙΣ ΔΕΝ ΜΠΟΡΕΙ ΝΑ ΧΡΗΣΙΜΟΠΟΙΗΣΕΙ ΤΟΝ EDITOR. Η
/// σύνδεση με Google αποδεικνύει μόνο ΠΟΙΟΣ είσαι — όχι ότι έχεις δουλειά εδώ.
///
/// Η λίστα ζει σε αρχείο ΕΞΩ από το repo (App_Data/) και δεν commit-άρεται:
/// είναι διευθύνσεις email πραγματικών ανθρώπων.
///
/// Ο διαχειριστής είναι πάντα εγκεκριμένος και δεν μπορεί να αφαιρεθεί από τη
/// λίστα — αλλιώς μια λάθος κλήση θα κλείδωνε έξω τον μόνο που μπορεί να
/// ξεκλειδώσει.
/// </summary>
public sealed class AccountStore
{
    private const string DefaultAdmin = "vassilisnperantzakis@gmail.com";
    private static readonly JsonSerializerOptions Json =
        new() { WriteIndented = true };

    private readonly string _path;
    private readonly object _lock = new();
    private Dictionary<string, Account> _all = new(StringComparer.OrdinalIgnoreCase);

    public string AdminEmail { get; }

    public AccountStore(IWebHostEnvironment env, IConfiguration config)
    {
        AdminEmail = (config["gravassistGadmin"] ?? DefaultAdmin).Trim().ToLowerInvariant();
        var dir = Path.Combine(env.ContentRootPath, "App_Data");
        Directory.CreateDirectory(dir);
        _path = Path.Combine(dir, "accounts.json");
        Load();
    }

    public static string Normalise(string? email) =>
        (email ?? "").Trim().ToLowerInvariant();

    public bool IsAdmin(string? email) => Normalise(email) == AdminEmail;

    public bool IsAllowed(string? email)
    {
        var key = Normalise(email);
        if (key.Length == 0) return false;
        if (key == AdminEmail) return true;
        lock (_lock)
            return _all.TryGetValue(key, out var a) && a.Allowed;
    }

    /// <summary>Όλοι οι λογαριασμοί: πρώτα όσοι περιμένουν έγκριση.</summary>
    public IReadOnlyList<Account> All()
    {
        lock (_lock)
            return _all.Values
                .OrderBy(a => a.Allowed)
                .ThenBy(a => a.Email, StringComparer.OrdinalIgnoreCase)
                .ToList();
    }

    /// <summary>Ο διαχειριστής προσκαλεί ένα email — μπαίνει ήδη εγκεκριμένο.</summary>
    public bool Invite(string? email) => Set(email, allowed: true, note: "invited");

    /// <summary>Έγκριση κάποιου που ζήτησε μόνος του.</summary>
    public bool Approve(string? email) => Set(email, allowed: true, note: "approved");

    /// <summary>Αφαίρεση πρόσβασης. Ο φάκελός του ΔΕΝ σβήνεται.</summary>
    public bool Revoke(string? email)
    {
        var key = Normalise(email);
        if (key.Length == 0 || key == AdminEmail) return false;
        lock (_lock)
        {
            if (!_all.TryGetValue(key, out var a)) return false;
            _all[key] = a with { Allowed = false, Note = "revoked" };
            Save();
        }

        return true;
    }

    /// <summary>
    /// Καταγράφει κάποιον που συνδέθηκε αλλά δεν επιτρέπεται ακόμα, ώστε ο
    /// διαχειριστής να τον δει και να αποφασίσει. ΔΕΝ του δίνει πρόσβαση.
    /// </summary>
    public void RecordPending(string? email)
    {
        var key = Normalise(email);
        if (key.Length == 0 || key == AdminEmail) return;
        lock (_lock)
        {
            if (_all.ContainsKey(key)) return;   // μην πατήσεις υπάρχουσα εγγραφή
            _all[key] = new Account(key, false, "asked", DateTime.UtcNow);
            Save();
        }
    }

    private bool Set(string? email, bool allowed, string note)
    {
        var key = Normalise(email);
        // Στοιχειώδης έλεγχος μορφής: το αρχείο το διαβάζει άνθρωπος και μια
        // γραμμή σκουπίδι εκεί μοιάζει με σφάλμα του προγράμματος.
        if (key.Length < 3 || !key.Contains('@') || key.Contains(' ')) return false;
        lock (_lock)
        {
            _all[key] = new Account(key, allowed, note, DateTime.UtcNow);
            Save();
        }

        return true;
    }

    private void Load()
    {
        if (!File.Exists(_path)) return;
        try
        {
            var list = JsonSerializer.Deserialize<List<Account>>(
                File.ReadAllText(_path)) ?? [];
            _all = list.ToDictionary(a => a.Email, a => a,
                                     StringComparer.OrdinalIgnoreCase);
        }
        catch (JsonException)
        {
            // Χαλασμένο αρχείο: ξεκινάμε άδειοι αντί να μη σηκωθεί ο editor.
            // Ο διαχειριστής μπαίνει πάντα, οπότε μπορεί να το ξαναφτιάξει.
            _all = new Dictionary<string, Account>(StringComparer.OrdinalIgnoreCase);
        }
    }

    private void Save() =>
        File.WriteAllText(_path, JsonSerializer.Serialize(_all.Values.ToList(), Json));
}
