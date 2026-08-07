namespace GravassistEditor.Models;

/// <summary>Ένα αρχείο του φακέλου levels/ όπως το βλέπει το UI.</summary>
/// <param name="Name">Το όνομα αρχείου, π.χ. <c>room_3.txt</c>.</param>
/// <param name="Room">Ο αριθμός αίθουσας, ή null αν το αρχείο δεν είναι αίθουσα.</param>
public sealed record LevelFileInfo(string Name, int? Room);

/// <summary>Μία ομάδα εξόδου με τον προορισμό της, όπως ταξιδεύει στο JSON.</summary>
/// <param name="Col">Στήλη του πάνω-αριστερού κελιού της ομάδας.</param>
/// <param name="Row">Γραμμή του πάνω-αριστερού κελιού της ομάδας.</param>
/// <param name="Room">Αριθμός αίθουσας προορισμού, ή null αν δεν έχει δηλωθεί.</param>
/// <param name="Cells">Πόσα κελιά έχει η ομάδα (πληροφοριακό, για το UI).</param>
public sealed record ExitDto(int Col, int Row, int? Room, int Cells);

/// <summary>Απάντηση φόρτωσης/δημιουργίας πίστας προς τον browser.</summary>
public sealed record LevelDto(
    string Name,
    IReadOnlyList<string> Rows,
    IReadOnlyList<string> Header,
    IReadOnlyList<string> Footer,
    IReadOnlyList<ExitDto> Exits,
    int? Room);

/// <summary>
/// Αίτημα αποθήκευσης από τον browser.
/// Η κεφαλή και η ουρά ταξιδεύουν πίσω αυτούσιες ώστε να διατηρηθούν τα σχόλια·
/// οι γραμμές «exit» της ουράς ξαναγράφονται από το <see cref="Exits"/>.
/// </summary>
public sealed class SaveLevelRequest
{
    public string Name { get; set; } = "";
    public List<string> Rows { get; set; } = [];
    public List<string> Header { get; set; } = [];
    public List<string> Footer { get; set; } = [];
    public List<ExitDto> Exits { get; set; } = [];
}

/// <summary>Ενιαία μορφή απάντησης σφάλματος (ελληνικό μήνυμα).</summary>
public sealed record ErrorDto(string Error);
