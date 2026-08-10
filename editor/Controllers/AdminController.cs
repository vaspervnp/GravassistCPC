using System.Security.Claims;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

/// <summary>
/// Οθόνη διαχείρισης λογαριασμών — ΜΟΝΟ για τον διαχειριστή.
///
/// Ο έλεγχος γίνεται σε κάθε action μέσω <see cref="Guard"/> και όχι με
/// attribute: το attribute θα ήθελε δική του πολιτική και ρόλο, και ένας
/// έλεγχος που χωράει σε δύο γραμμές δεν αξίζει τρία σημεία ρύθμισης όπου
/// μπορεί να ξεχαστεί το ένα.
/// </summary>
[Route("admin")]
public sealed class AdminController(AccountStore accounts) : Controller
{
    private bool IsAdmin =>
        accounts.IsAdmin(User.FindFirstValue(ClaimTypes.Email));

    private IActionResult? Guard() =>
        IsAdmin ? null : StatusCode(404);   // 404 και όχι 403: η ύπαρξη της
                                            // σελίδας δεν αφορά κανέναν άλλον

    [HttpGet("")]
    public IActionResult Index()
    {
        if (Guard() is { } stop) return stop;
        ViewData["Admin"] = accounts.AdminEmail;
        return View(accounts.All());
    }

    [HttpPost("invite")]
    [ValidateAntiForgeryToken]
    public IActionResult Invite(string email)
    {
        if (Guard() is { } stop) return stop;
        TempData["Msg"] = accounts.Invite(email)
            ? $"Invited {AccountStore.Normalise(email)}."
            : "That does not look like an email address.";
        return RedirectToAction(nameof(Index));
    }

    [HttpPost("approve")]
    [ValidateAntiForgeryToken]
    public IActionResult Approve(string email)
    {
        if (Guard() is { } stop) return stop;
        TempData["Msg"] = accounts.Approve(email)
            ? $"Approved {AccountStore.Normalise(email)}."
            : "Could not approve that address.";
        return RedirectToAction(nameof(Index));
    }

    [HttpPost("revoke")]
    [ValidateAntiForgeryToken]
    public IActionResult Revoke(string email)
    {
        if (Guard() is { } stop) return stop;
        TempData["Msg"] = accounts.Revoke(email)
            ? $"Revoked {AccountStore.Normalise(email)}. Their folder is kept."
            : "Could not revoke that address.";
        return RedirectToAction(nameof(Index));
    }
}
