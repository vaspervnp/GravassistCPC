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
/// <param name="TwoWay">Υπάρχει πόρτα επιστροφής στην άλλη αίθουσα;</param>
/// <param name="ArriveCol">Στήλη του κελιού άφιξης, ή null = να το βρει το παιχνίδι.</param>
/// <param name="ArriveRow">Γραμμή του κελιού άφιξης, ή null = να το βρει το παιχνίδι.</param>
/// <param name="ArriveG">Φορά βαρύτητας άφιξης (0..7), ή null = της αίθουσας.</param>
public sealed record ExitDto(int Col, int Row, int? Room, int Cells, bool TwoWay,
    int? ArriveCol = null, int? ArriveRow = null, int? ArriveG = null);

/// <summary>
/// Μία ομάδα τηλεμεταφοράς με τον προορισμό της, όπως ταξιδεύει στο JSON.
/// </summary>
/// <param name="Col">Στήλη του πάνω-αριστερού κελιού της ομάδας.</param>
/// <param name="Row">Γραμμή του πάνω-αριστερού κελιού της ομάδας.</param>
/// <param name="DestCol">Στήλη του κελιού προορισμού, ή null αν δεν έχει δηλωθεί.</param>
/// <param name="DestRow">Γραμμή του κελιού προορισμού, ή null αν δεν έχει δηλωθεί.</param>
/// <param name="Cells">Πόσα κελιά έχει η ομάδα (πληροφοριακό, για το UI).</param>
public sealed record TeleportDto(int Col, int Row, int? DestCol, int? DestRow, int Cells);

/// <summary>Μία ομάδα διακόπτη/πόρτας/κλειδαριάς/κλειδιού με το κανάλι της.</summary>
/// <param name="Kind">«sw», «gate», «lock» ή «key».</param>
/// <param name="Value">Κανάλι (διακόπτες, πόρτες) ή ταυτότητα (κλειδιά, κλειδαριές).</param>
public sealed record AttrDto(string Kind, int Col, int Row, int Value, int Cells);

/// <summary>
/// Ένας πυργίσκος με τις τρεις ρυθμίσεις του. Χωριστός από το
/// <see cref="AttrDto"/>, που κουβαλά ΕΝΑΝ αριθμό — δες <see cref="TurretGraph"/>.
/// </summary>
/// <param name="Channel">Κανάλι διακόπτη 0..7· 0 = ακαλωδίωτος.</param>
/// <param name="Reload">Δευτερόλεπτα ανάμεσα σε δύο βολές «όταν σε βλέπει».</param>
/// <param name="Auto">0 = μόνο όταν σε βλέπει· αλλιώς ρυθμός σε δευτερόλεπτα.</param>
public sealed record TurretDto(int Col, int Row, int Channel, int Reload, int Auto,
    int Cells);

/// <summary>
/// Μία κινούμενη πλατφόρμα. Το μέγεθος δεν ταξιδεύει — βγαίνει από το πλέγμα.
/// </summary>
/// <param name="DestCol">Το δεύτερο άκρο της διαδρομής, σε κελιά.</param>
/// <param name="Channel">Κανάλι διακόπτη 0..7· 0 = δεν τη σταματά κανείς.</param>
/// <param name="Speed">Pixel ανά δευτερόλεπτο.</param>
public sealed record PlatformDto(int Col, int Row, int DestCol, int DestRow,
    int Channel, int Speed, int Cells);

/// <summary>Απάντηση φόρτωσης/δημιουργίας πίστας προς τον browser.</summary>
public sealed record LevelDto(
    string Name,
    IReadOnlyList<string> Rows,
    IReadOnlyList<string> Header,
    IReadOnlyList<string> Footer,
    IReadOnlyList<ExitDto> Exits,
    IReadOnlyList<TeleportDto> Teleports,
    int? Room,
    int Gravity,
    IReadOnlyList<AttrDto> Attrs,
    IReadOnlyList<TurretDto> Turrets,
    IReadOnlyList<PlatformDto> Platforms);

/// <summary>
/// Αίτημα αποθήκευσης από τον browser.
/// Η κεφαλή και η ουρά ταξιδεύουν πίσω αυτούσιες ώστε να διατηρηθούν τα σχόλια·
/// οι γραμμές «exit» της ουράς ξαναγράφονται από το <see cref="Exits"/> και οι
/// γραμμές «tp» από το <see cref="Teleports"/>.
/// </summary>
public sealed class SaveLevelRequest
{
    public string Name { get; set; } = "";
    public List<string> Rows { get; set; } = [];
    public List<string> Header { get; set; } = [];
    public List<string> Footer { get; set; } = [];
    public List<ExitDto> Exits { get; set; } = [];
    public List<TeleportDto> Teleports { get; set; } = [];

    /// <summary>Αρχική φορά βαρύτητας της αίθουσας (0..7) — η γραμμή «gravity N».</summary>
    public int Gravity { get; set; }

    /// <summary>Καλωδίωση διακοπτών/πορτών και κλειδιών/κλειδαριών.</summary>
    public List<AttrDto> Attrs { get; set; } = [];

    /// <summary>Οι πυργίσκοι — μία εγγραφή ανά ομάδα κελιών.</summary>
    public List<TurretDto> Turrets { get; set; } = [];

    /// <summary>Οι κινούμενες πλατφόρμες — μία εγγραφή ανά ομάδα κελιών.</summary>
    public List<PlatformDto> Platforms { get; set; } = [];
}

/// <summary>Ενιαία μορφή απάντησης σφάλματος (ελληνικό μήνυμα).</summary>
public sealed record ErrorDto(string Error);

/// <summary>Αίτημα αντιγραφής ή μετακίνησης αίθουσας.</summary>
/// <param name="From">Αριθμός της αίθουσας πηγής.</param>
/// <param name="To">Νέος αριθμός (μόνο για μετακίνηση).</param>
public sealed record RoomOpRequest(int From, int? To);
