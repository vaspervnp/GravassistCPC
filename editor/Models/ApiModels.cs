namespace GravassistEditor.Models;

/// <summary>Απάντηση φόρτωσης/δημιουργίας πίστας προς τον browser.</summary>
public sealed record LevelDto(
    string Name,
    IReadOnlyList<string> Rows,
    IReadOnlyList<string> Header,
    IReadOnlyList<string> Footer);

/// <summary>
/// Αίτημα αποθήκευσης από τον browser.
/// Η κεφαλή και η ουρά ταξιδεύουν πίσω αυτούσιες ώστε να διατηρηθούν τα σχόλια.
/// </summary>
public sealed class SaveLevelRequest
{
    public string Name { get; set; } = "";
    public List<string> Rows { get; set; } = [];
    public List<string> Header { get; set; } = [];
    public List<string> Footer { get; set; } = [];
}

/// <summary>Ενιαία μορφή απάντησης σφάλματος (ελληνικό μήνυμα).</summary>
public sealed record ErrorDto(string Error);
