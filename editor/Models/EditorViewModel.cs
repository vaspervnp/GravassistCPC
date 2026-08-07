namespace GravassistEditor.Models;

/// <summary>Ό,τι χρειάζεται το view για να στηθεί ο editor.</summary>
public sealed class EditorViewModel
{
    /// <summary>Ο κατάλογος τύπων κελιών — παλέτα, σχήματα και έγκυροι χαρακτήρες.</summary>
    public required IReadOnlyList<TileType> Tiles { get; init; }

    /// <summary>Τα διαθέσιμα αρχεία στον φάκελο levels/.</summary>
    public required IReadOnlyList<string> Files { get; init; }

    /// <summary>Η απόλυτη διαδρομή του φακέλου πιστών (εμφανίζεται στο UI).</summary>
    public required string LevelsPath { get; init; }

    public int Cols => TileCatalog.Cols;
    public int Rows => TileCatalog.Rows;
    public char EmptySymbol => TileCatalog.EmptySymbol;
    public char SolidSymbol => TileCatalog.SolidSymbol;
}
