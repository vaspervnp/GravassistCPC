using System.Diagnostics;
using System.Security.Claims;
using GravassistEditor.Models;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

public sealed class HomeController(LevelStore store, AccountStore accounts) : Controller
{
    /// <summary>Η σελίδα του editor. Παίρνει τον κατάλογο τύπων και τη λίστα πιστών.</summary>
    public IActionResult Index()
    {
        // Το κουμπί «Publish» δεν καν αποδίδεται σε όποιον δεν το έχει. Ο
        // πραγματικός έλεγχος είναι στον LevelsController· εδώ απλώς δεν
        // δείχνουμε πόρτα που δεν ανοίγει.
        ViewData["CanPublish"] =
            accounts.CanPublish(User.FindFirstValue(ClaimTypes.Email));
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
