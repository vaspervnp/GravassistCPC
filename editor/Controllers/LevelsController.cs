using System.Security.Claims;
using GravassistEditor.Models;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

/// <summary>
/// API πιστών: λίστα, φόρτωση, δημιουργία, αποθήκευση.
/// Τα μηνύματα σφάλματος είναι στα ΑΓΓΛΙΚΑ (όπως όλο το UI του editor) και
/// εμφανίζονται όπως έχουν· τα σχόλια του κώδικα μένουν ελληνικά.
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
            if (!store.Exists(name)) return NotFound(new ErrorDto($"Level \"{name}\" not found."));
            var doc = store.Load(name);
            return Ok(ToDto(Path.GetFileName(store.ResolvePath(name)), doc));
        }
        catch (LevelFormatException ex)
        {
            return BadRequest(new ErrorDto(ex.Message));
        }
        catch (IOException ex)
        {
            return BadRequest(new ErrorDto($"Read error: {ex.Message}"));
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
                    e.ArriveCol, e.ArriveRow, e.ArriveG)));

            // ΜΕΤΑ τις εξόδους, ώστε η ουρά να μένει «… exit … / tp …» — η ίδια
            // σειρά με τα υπάρχοντα αρχεία (round-trip χωρίς αλλαγές).
            // Ομάδα χωρίς προορισμό δεν γράφει γραμμή· την πιάνει η επικύρωση ως
            // προειδοποίηση, γιατί απλώς δεν κάνει τίποτα στο παιχνίδι.
            doc.SetTeleportLinks(request.Teleports
                .Where(t => t.DestCol is not null && t.DestRow is not null)
                .Select(t => new TeleportLink(t.Col, t.Row, t.DestCol!.Value, t.DestRow!.Value)));

            doc.SetAttrLinks(request.Attrs
                .Select(a => new AttrLink(a.Kind, a.Col, a.Row, a.Value)));

            doc.StartGravity = request.Gravity;

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
            return BadRequest(new ErrorDto($"Write error: {ex.Message}"));
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
            return BadRequest(new ErrorDto($"Write error: {ex.Message}"));
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
        catch (IOException ex) { return BadRequest(new ErrorDto($"Write error: {ex.Message}")); }
    }

    /// <summary>
    /// Μετακινεί αίθουσα σε άλλον αριθμό, ενημερώνοντας ΟΛΕΣ τις πόρτες που
    /// δείχνουν σε αυτήν.
    /// </summary>
    [HttpPost("room/move")]
    public IActionResult MoveRoom([FromBody] RoomOpRequest req)
    {
        if (req.To is null or < 1 or > 9999)
            return BadRequest(new ErrorDto("The new number must be 1..9999."));
        try
        {
            var touched = store.MoveRoom(req.From, req.To.Value);
            var name = RoomNaming.FileName(req.To.Value);
            return Ok(new { name, touched, dto = ToDto(name, store.Load(name)) });
        }
        catch (LevelFormatException ex) { return BadRequest(new ErrorDto(ex.Message)); }
        catch (IOException ex) { return BadRequest(new ErrorDto($"Write error: {ex.Message}")); }
    }

    // ------------------------------------------------------------- αρχείο zip
    //
    // Ο φάκελος ζει στον server και ο χρήστης δεν τον φτάνει αλλιώς. Το zip
    // είναι ο τρόπος να πάρει τη δουλειά του μαζί του, να τη δώσει σε άλλον ή
    // να τη γυρίσει πίσω μετά από πείραμα.

    /// <summary>GET /api/levels/export — όλες οι πίστες σε ένα .zip.</summary>
    [HttpGet("export")]
    public IActionResult Export([FromServices] LevelArchive archive)
    {
        var bytes = archive.Export(store.RootPath);
        return File(bytes, "application/zip", "gravassist-levels.zip");
    }

    /// <summary>
    /// POST /api/levels/import — εισαγωγή από .zip.
    /// Με <c>preview=true</c> λέει μόνο τι ΘΑ γινόταν, χωρίς να γράψει.
    /// </summary>
    [HttpPost("import")]
    [RequestSizeLimit(LevelArchive.MaxTotalBytes)]
    public IActionResult Import(IFormFile file, bool preview,
                                [FromServices] LevelArchive archive)
    {
        if (file is null || file.Length == 0)
            return BadRequest(new ErrorDto("Choose a .zip file first."));
        try
        {
            using var s = file.OpenReadStream();
            var plan = preview ? archive.Plan(s, store.RootPath)
                               : archive.Import(s, store.RootPath);
            var errors = plan.Count(e => e.Kind == "error");
            return Ok(new
            {
                ok = errors == 0,
                written = preview ? 0 : plan.Count(e => e.Kind is "new" or "changed"),
                changes = plan.Select(e => new { name = e.Name, kind = e.Kind, detail = e.Detail }),
            });
        }
        catch (IOException ex) { return BadRequest(new ErrorDto($"Write error: {ex.Message}")); }
    }

    // ---------------------------------------------------------- δημοσίευση
    //
    // Ο editor γράφει στον ΠΡΟΣΩΠΙΚΟ φάκελο του λογαριασμού. Η δημοσίευση
    // αντιγράφει τις αίθουσές του στο ΚΟΙΝΟ levels/ — αυτό που παρακολουθεί το
    // git και που σπέρνει κάθε νέο λογαριασμό. Γι' αυτό είναι χωριστό δικαίωμα
    // που δίνει ο διαχειριστής, και γι' αυτό ελέγχεται ΕΔΩ και όχι μόνο
    // κρύβοντας το κουμπί: κρυμμένο κουμπί ΔΕΝ είναι έλεγχος πρόσβασης.

    private const string NoPublish =
        "This account is not allowed to publish to the shared levels folder.";

    private string? Email => User.FindFirstValue(ClaimTypes.Email);

    /// <summary>GET /api/levels/publish — τι ΘΑ άλλαζε η δημοσίευση. Δεν γράφει.</summary>
    [HttpGet("publish")]
    public IActionResult PublishPreview([FromServices] AccountStore accounts,
                                        [FromServices] UserWorkspace workspace)
    {
        if (!accounts.CanPublish(Email)) return StatusCode(403, new ErrorDto(NoPublish));
        var changes = workspace.PublishPreview(store.RootPath)
            .Select(c => new { name = c.Name, kind = c.Kind });
        return Ok(new { shared = workspace.SharedRoot, changes });
    }

    /// <summary>POST /api/levels/publish — αντιγράφει τις αίθουσες στο κοινό levels/.</summary>
    [HttpPost("publish")]
    public IActionResult Publish([FromServices] AccountStore accounts,
                                 [FromServices] UserWorkspace workspace)
    {
        if (!accounts.CanPublish(Email)) return StatusCode(403, new ErrorDto(NoPublish));
        try
        {
            return Ok(new { written = workspace.Publish(store.RootPath) });
        }
        catch (IOException ex) { return BadRequest(new ErrorDto($"Write error: {ex.Message}")); }
    }

    /// <summary>GET /api/levels/pull — τι ΘΑ αντικαθιστούσε το τράβηγμα. Δεν γράφει.</summary>
    [HttpGet("pull")]
    public IActionResult PullPreview([FromServices] AccountStore accounts,
                                     [FromServices] UserWorkspace workspace)
    {
        if (!accounts.CanPublish(Email)) return StatusCode(403, new ErrorDto(NoPublish));
        var changes = workspace.PullPreview(store.RootPath)
            .Select(c => new { name = c.Name, kind = c.Kind });
        return Ok(new { shared = workspace.SharedRoot, changes });
    }

    /// <summary>POST /api/levels/pull — φέρνει τα κοινά levels/ πάνω στα δικά του.</summary>
    [HttpPost("pull")]
    public IActionResult Pull([FromServices] AccountStore accounts,
                              [FromServices] UserWorkspace workspace)
    {
        if (!accounts.CanPublish(Email)) return StatusCode(403, new ErrorDto(NoPublish));
        try
        {
            return Ok(new { written = workspace.Pull(store.RootPath) });
        }
        catch (IOException ex) { return BadRequest(new ErrorDto($"Write error: {ex.Message}")); }
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
                    link?.TwoWay ?? false, link?.ArriveCol, link?.ArriveRow,
                    link?.ArriveG);
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

        // Η αυθεντία για το ΠΟΙΕΣ ομάδες υπάρχουν είναι πάντα το πλέγμα· η ουρά
        // δίνει μόνο τιμές, και όποια δήλωση δεν πέφτει πάνω σε ομάδα αγνοείται.
        var byKind = doc.AttrLinks()
            .GroupBy(l => (l.Kind, l.Col, l.Row))
            .ToDictionary(g => g.Key, g => g.Last().Value);

        var attrs = new List<AttrDto>();
        foreach (var (kind, _) in AttrGraph.Kinds)
            foreach (var g in doc.AttrGroups(kind))
                attrs.Add(new AttrDto(kind, g.Col, g.Row,
                    byKind.TryGetValue((kind, g.Col, g.Row), out var v) ? v : 0,
                    g.Cells.Count));

        return new LevelDto(name, doc.Rows, doc.Header, doc.Footer,
            exits, teleports, RoomNaming.NumberOf(name), doc.StartGravity, attrs);
    }
}
