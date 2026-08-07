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
    /// <summary>GET /api/levels — τα ονόματα των αρχείων στον φάκελο levels/.</summary>
    [HttpGet]
    public IActionResult Index() => Ok(new { path = store.RootPath, files = store.List() });

    /// <summary>GET /api/levels/{name} — φόρτωση πίστας.</summary>
    [HttpGet("{name}")]
    public IActionResult Load(string name)
    {
        try
        {
            if (!store.Exists(name)) return NotFound(new ErrorDto($"Δεν βρέθηκε η πίστα «{name}»."));
            var doc = store.Load(name);
            return Ok(new LevelDto(name, doc.Rows, doc.Header, doc.Footer));
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

    /// <summary>POST /api/levels — αποθήκευση πίστας.</summary>
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
            store.Save(request.Name, doc);
            return Ok(new { saved = Path.GetFileName(store.ResolvePath(request.Name)) });
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
        return Ok(new LevelDto("", doc.Rows, doc.Header, doc.Footer));
    }
}
