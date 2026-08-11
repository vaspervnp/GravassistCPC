using System.Security.Cryptography;
using System.Text;

namespace GravassistEditor.Services;

/// <summary>Το αποτέλεσμα μιας αίτησης κωδικού.</summary>
public enum CodeRequest
{
    /// <summary>Φτιάχτηκε κωδικός — στείλ' τον.</summary>
    Sent,
    /// <summary>Ζητήθηκε πολύ γρήγορα ξανά· ο προηγούμενος ισχύει ακόμα.</summary>
    TooSoon,
    /// <summary>Πολλές αιτήσεις. Δεν φτιάχνεται κωδικός.</summary>
    TooMany,
}

/// <summary>
/// Οι εξάψήφιοι κωδικοί σύνδεσης με email.
///
/// ΑΝΤΙ ΓΙΑ ΚΩΔΙΚΟ ΠΡΟΣΒΑΣΗΣ: ο κωδικός που φτάνει στο γραμματοκιβώτιο ΕΙΝΑΙ η
/// απόδειξη ταυτότητας. Ό,τι ισχύει για έναν κωδικό μιας χρήσης ισχύει κι εδώ:
/// σύντομη ζωή, λίγες προσπάθειες, και αποθήκευση ΜΟΝΟ του hash — ένα log ή
/// ένα dump μνήμης δεν πρέπει να δίνει σε κανέναν έτοιμη σύνδεση.
///
/// ΖΕΙ ΣΤΗ ΜΝΗΜΗ. Ένα restart ακυρώνει όσους κωδικούς είναι στον αέρα· ο
/// χρήστης ζητά καινούριο. Το να γράφαμε στον δίσκο ενεργά διαπιστευτήρια για
/// να γλιτώσουμε αυτή την ενόχληση θα ήταν κακή ανταλλαγή.
///
/// ΟΙ ΦΡΑΓΜΟΙ ΔΕΝ ΕΙΝΑΙ ΓΙΑ ΤΟΝ ΧΡΗΣΤΗ, ΕΙΝΑΙ ΓΙΑ ΤΑ ΘΥΜΑΤΑ: χωρίς αυτούς η
/// φόρμα σύνδεσης γίνεται μηχανή αποστολής email προς οποιαδήποτε διεύθυνση.
/// Γι' αυτό υπάρχει όριο ανά διεύθυνση, ανά IP και συνολικό.
/// </summary>
public sealed class LoginCodes(ILogger<LoginCodes> log)
{
    public static readonly TimeSpan Lifetime = TimeSpan.FromMinutes(10);
    public static readonly TimeSpan Cooldown = TimeSpan.FromSeconds(60);
    private static readonly TimeSpan Window = TimeSpan.FromHours(1);

    private const int MaxAttempts = 5;
    private const int PerEmailPerHour = 5;
    private const int PerIpPerHour = 10;
    private const int TotalPerHour = 100;

    private sealed class Entry
    {
        public byte[] Hash = [];
        public byte[] Salt = [];
        public DateTime Expires;
        public DateTime Sent;
        public int Attempts;
    }

    private readonly object _lock = new();
    private readonly Dictionary<string, Entry> _live = new(StringComparer.OrdinalIgnoreCase);
    private readonly List<(DateTime When, string Email, string Ip)> _recent = [];

    /// <summary>
    /// Φτιάχνει κωδικό για τη διεύθυνση. Ο κωδικός επιστρέφεται ΜΙΑ φορά, για
    /// να σταλεί — δεν ξαναδιαβάζεται από πουθενά.
    /// </summary>
    public (CodeRequest Result, string? Code) Issue(string email, string ip)
    {
        var key = AccountStore.Normalise(email);
        var now = DateTime.UtcNow;
        lock (_lock)
        {
            Prune(now);

            if (_live.TryGetValue(key, out var live) && now - live.Sent < Cooldown)
                return (CodeRequest.TooSoon, null);

            if (_recent.Count >= TotalPerHour ||
                _recent.Count(r => r.Email == key) >= PerEmailPerHour ||
                _recent.Count(r => r.Ip == ip) >= PerIpPerHour)
            {
                log.LogWarning("Φραγή κωδικών σύνδεσης: {Email} από {Ip}.", key, ip);
                return (CodeRequest.TooMany, null);
            }

            // 000000..999999 με ομοιόμορφη κατανομή· το RandomNumberGenerator
            // και όχι το Random, γιατί ο κωδικός ΕΙΝΑΙ το διαπιστευτήριο.
            var code = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
            var salt = RandomNumberGenerator.GetBytes(16);
            _live[key] = new Entry
            {
                Salt = salt,
                Hash = Hash(code, salt),
                Expires = now + Lifetime,
                Sent = now,
                Attempts = MaxAttempts,
            };
            _recent.Add((now, key, ip));
            return (CodeRequest.Sent, code);
        }
    }

    /// <summary>
    /// Σωστός κωδικός; Καταναλώνεται με την επιτυχία — ένας κωδικός, μία
    /// σύνδεση. Μετά από <see cref="MaxAttempts"/> αποτυχίες σβήνεται, ώστε να
    /// μη μαντεύεται με επανάληψη.
    /// </summary>
    public bool Verify(string email, string? code)
    {
        var key = AccountStore.Normalise(email);
        var given = (code ?? "").Trim();
        var now = DateTime.UtcNow;
        lock (_lock)
        {
            Prune(now);
            if (!_live.TryGetValue(key, out var e)) return false;
            if (now > e.Expires) { _live.Remove(key); return false; }

            // Σταθερού χρόνου: μια σύγκριση που σταματά στο πρώτο λάθος ψηφίο
            // διαρρέει πόσα ψηφία βρήκες.
            if (CryptographicOperations.FixedTimeEquals(Hash(given, e.Salt), e.Hash))
            {
                _live.Remove(key);
                return true;
            }

            if (--e.Attempts <= 0)
            {
                _live.Remove(key);
                log.LogWarning("Πολλές λάθος προσπάθειες κωδικού για {Email}.", key);
            }

            return false;
        }
    }

    /// <summary>Υπάρχει κωδικός σε ισχύ; Το χρησιμοποιεί μόνο το UI.</summary>
    public bool Pending(string email)
    {
        var key = AccountStore.Normalise(email);
        lock (_lock)
        {
            Prune(DateTime.UtcNow);
            return _live.ContainsKey(key);
        }
    }

    private void Prune(DateTime now)
    {
        _recent.RemoveAll(r => now - r.When > Window);
        foreach (var key in _live.Where(p => now > p.Value.Expires)
                                 .Select(p => p.Key).ToList())
            _live.Remove(key);
    }

    private static byte[] Hash(string code, byte[] salt) =>
        SHA256.HashData([.. salt, .. Encoding.UTF8.GetBytes(code)]);
}
