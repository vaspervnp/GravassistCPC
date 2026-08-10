using GravassistEditor.Models;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

/// <summary>
/// API πιστών: λίστα, φόρτωση, δημιουργία, αποθήκευση.
/// Όλα τα μηνύματα σφάλματος είναι στα ελληνικά και εμφανίζονται όπως έχουν στο UI.
/// </summary>
[ApiController]
[Route("api/levels")]
public sealed class LevelsController(LevelStore store) : ControllerBase
{
    /// <summary>GET /api/levels — τα αρχεία στον φάκελο levels/ (αίθουσες πρώτα, αριθμητικά).</summary>
    [HttpGet]
    public IActionResult Index() => Ok(new { path = store.RootPath, files = store.List() });

    /// <summary>GET /api/levels/{name} — φόρτωση πίστας μαζί με τις ομάδες εξόδου.</summary>
    [HttpGet("{name}")]
    public IActionResult Load(string name)
    {
        try
        {
            if (!store.Exists(name)) return NotFound(new ErrorDto($"Δεν βρέθηκε η πίστα «{name}»."));
            var doc = store.Load(name);
            return Ok(ToDto(Path.GetFileName(store.ResolvePath(name)), doc));
        }
        catch (LevelFormatException ex)
        {
            return BadRequest(new ErrorDto(ex.Message));
        }
        catch (IOException ex)
        {
            return BadRequest(new ErrorDto($"Σφάλμα ανάγνωσης: {ex.Message}"));
        }
    }

    /// <summary>POST /api/levels — αποθήκευση πίστας (και των συνδέσεων εξόδων).</summary>
    [HttpPost]
    public IActionResult Save([FromBody] SaveLevelRequest request)
    {
        try
        {
            var doc = new LevelDocument
            {
                Header = request.Header,
                Footer = request.Footer,
                Rows = request.Rows,
            };

            // Οι δηλώσεις εξόδου ξαναγράφονται ΟΛΕΣ από την κατάσταση του editor:
            // ό,τι δεν έχει προορισμό μένει έξω και το πιάνει η επικύρωση.
            doc.SetExitLinks(request.Exits
                .Where(e => e.Room is not null)
                .Select(e => new ExitLink(e.Col, e.Row, e.Room!.Value, e.TwoWay,
                    e.ArriveCol, e.ArriveRow)));

            // ΜΕΤΑ τις εξόδους, ώστε η ουρά να μένει «… exit … / tp …» — η ίδια
            // σειρά με τα υπάρχοντα αρχεία (round-trip χωρίς αλλαγές).
            // Ομάδα χωρίς προορισμό δεν γράφει γραμμή· την πιάνει η επικύρωση ως
            // προειδοποίηση, γιατί απλώς δεν κάνει τίποτα στο παιχνίδι.
            doc.SetTeleportLinks(request.Teleports
                .Where(t => t.DestCol is not null && t.DestRow is not null)
                .Select(t => new TeleportLink(t.Col, t.Row, t.DestCol!.Value, t.DestRow!.Value)));

            var warnings = store.Save(request.Name, doc);
            return Ok(new
            {
                saved = Path.GetFileName(store.ResolvePath(request.Name)),
                warnings,
            });
        }
        catch (LevelFormatException ex)
        {
            return BadRequest(new ErrorDto(ex.Message));
        }
        catch (IOException ex)
        {
            return BadRequest(new ErrorDto($"Σφάλμα εγγραφής: {ex.Message}"));
        }
    }

    /// <summary>GET /api/levels/new — άδεια πίστα με περίγραμμα (δεν γράφεται στον δίσκο).</summary>
    [HttpGet("new")]
    public IActionResult Blank()
    {
        var doc = LevelDocument.CreateEmpty();
        return Ok(ToDto("", doc));
    }

    /// <summary>
    /// POST /api/levels/room — νέα ΑΙΘΟΥΣΑ με τον επόμενο ελεύθερο αριθμό.
    /// Το αρχείο γράφεται αμέσως, ώστε να μπορούν άλλες αίθουσες να δείχνουν σ' αυτό.
    /// </summary>
    [HttpPost("room")]
    public IActionResult NewRoom()
    {
        try
        {
            var (_, name, doc) = store.CreateRoom();
            return Ok(ToDto(name, doc));
        }
        catch (LevelFormatException ex)
        {
            return BadRequest(new ErrorDto(ex.Message));
        }
        catch (IOException ex)
        {
            return BadRequest(new ErrorDto($"Σφάλμα εγγραφής: {ex.Message}"));
        }
    }

    /// <summary>Αντιγράφει αίθουσα στον επόμενο ελεύθερο αριθμό.</summary>
    [HttpPost("room/copy")]
    public IActionResult CopyRoom([FromBody] RoomOpRequest req)
    {
        try
        {
            var (_, name, doc) = store.CopyRoom(req.From);
            return Ok(ToDto(name, doc));
        }
        catch (LevelFormatException ex) { return BadRequest(new ErrorDto(ex.Message)); }
        catch (IOException ex) { return BadRequest(new ErrorDto($"Σφάλμα εγγραφής: {ex.Message}")); }
    }

    /// <summary>
    /// Μετακινεί αίθουσα σε άλλον αριθμό, ενημερώνοντας ΟΛΕΣ τις πόρτες που
    /// δείχνουν σε αυτήν.
    /// </summary>
    [HttpPost("room/move")]
    public IActionResult MoveRoom([FromBody] RoomOpRequest req)
    {
        if (req.To is null or < 1 or > 9999)
            return BadRequest(new ErrorDto("Ο νέος αριθμός πρέπει να είναι 1..9999."));
        try
        {
            var touched = store.MoveRoom(req.From, req.To.Value);
            var name = RoomNaming.FileName(req.To.Value);
            return Ok(new { name, touched, dto = ToDto(name, store.Load(name)) });
        }
        catch (LevelFormatException ex) { return BadRequest(new ErrorDto(ex.Message)); }
        catch (IOException ex) { return BadRequest(new ErrorDto($"Σφάλμα εγγραφής: {ex.Message}")); }
    }

    /// <summary>
    /// Ενώνει τις ομάδες εξόδου και τηλεμεταφοράς του πλέγματος με τους
    /// προορισμούς της ουράς. Η αυθεντία για το ΠΟΙΕΣ είναι οι ομάδες είναι πάντα
    /// το πλέγμα· η ουρά δίνει μόνο προορισμούς και όποια δήλωση δεν ταιριάζει σε
    /// ομάδα αγνοείται.
    /// </summary>
    private static LevelDto ToDto(string name, LevelDocument doc)
    {
        var byAnchor = doc.ExitLinks()
            .GroupBy(l => (l.Col, l.Row))
            .ToDictionary(g => g.Key, g => g.Last());

        var exits = doc.ExitGroups()
            .Select(g =>
            {
                byAnchor.TryGetValue((g.Col, g.Row), out var link);
                return new ExitDto(g.Col, g.Row, link?.Room, g.Cells.Count,
                    link?.TwoWay ?? false, link?.ArriveCol, link?.ArriveRow);
            })
            .ToList();

        var tpByAnchor = doc.TeleportLinks()
            .GroupBy(l => (l.Col, l.Row))
            .ToDictionary(g => g.Key, g => g.Last());

        var teleports = doc.TeleportGroups()
            .Select(g => tpByAnchor.TryGetValue((g.Col, g.Row), out var link)
                ? new TeleportDto(g.Col, g.Row, link.DestCol, link.DestRow, g.Cells.Count)
                : new TeleportDto(g.Col, g.Row, null, null, g.Cells.Count))
            .ToList();

        return new LevelDto(name, doc.Rows, doc.Header, doc.Footer,
            exits, teleports, RoomNaming.NumberOf(name));
    }
}
