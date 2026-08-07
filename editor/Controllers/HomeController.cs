using System.Diagnostics;
using GravassistEditor.Models;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

public sealed class HomeController(LevelStore store) : Controller
{
    /// <summary>Η σελίδα του editor. Παίρνει τον κατάλογο τύπων και τη λίστα πιστών.</summary>
    public IActionResult Index()
    {
        return View(new EditorViewModel
        {
            Tiles = TileCatalog.All,
            Files = store.List(),
            LevelsPath = store.RootPath,
        });
    }

    [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
    public IActionResult Error()
    {
        return View(new ErrorViewModel
        {
            RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier,
        });
    }
}
