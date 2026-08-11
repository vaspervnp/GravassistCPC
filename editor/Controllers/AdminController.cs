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
public sealed class AdminController(AccountStore accounts, Mailer mail) : Controller
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
        ViewData["Mail"] = mail.IsConfigured;
        return View(accounts.All());
    }

    /// <summary>
    /// Στέλνει δοκιμαστικό email στον ίδιο τον διαχειριστή.
    ///
    /// ΓΙΑΤΙ ΥΠΑΡΧΕΙ: μια ρύθμιση SMTP σπάνια δουλεύει με την πρώτη (λάθος
    /// θύρα, app password, αποστολέας που δεν ταιριάζει με τον λογαριασμό).
    /// Χωρίς αυτό θα το ανακάλυπτες μέσα από τη φόρμα σύνδεσης, όπου η
    /// απάντηση είναι σκόπιμα αόριστη για να μη διαρρέει ποια email υπάρχουν.
    /// </summary>
    [HttpPost("mailtest")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> MailTest()
    {
        if (Guard() is { } stop) return stop;
        if (!mail.IsConfigured)
        {
            TempData["Msg"] = $"No mail settings: {Mailer.HostVar} and {Mailer.FromVar} "
                              + "must be set in the environment.";
            return RedirectToAction(nameof(Index));
        }

        var ok = await mail.SendAsync(accounts.AdminEmail,
            "GRAVASSIST editor — test message",
            $"""
             This is a test from the GRAVASSIST editor.

             If you are reading it, the mail settings work and sign-in codes
             and invitations will go out.

             Sent from: {mail.From}
             """);
        TempData["Msg"] = ok
            ? $"Test message sent to {accounts.AdminEmail}."
            : "Sending failed. The exact error from the mail server is in the editor's console log.";
        return RedirectToAction(nameof(Index));
    }

    [HttpPost("invite")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Invite(string email)
    {
        if (Guard() is { } stop) return stop;
        var who = AccountStore.Normalise(email);
        if (!accounts.Invite(email))
        {
            TempData["Msg"] = "That does not look like an email address.";
            return RedirectToAction(nameof(Index));
        }

        // Ο λογαριασμός είναι ΗΔΗ εγκεκριμένος· το email είναι η ειδοποίηση.
        // Αν δεν φύγει, η πρόσκληση εξακολουθεί να ισχύει — γι' αυτό το
        // μήνυμα λέει ξεχωριστά τι έγινε και τι δεν έγινε.
        var url = $"{mail.BaseUrl(Request)}/accounts/login";
        var sent = mail.IsConfigured && await mail.SendAsync(who,
            "You have been invited to the GRAVASSIST level editor",
            $"""
             You can now use the GRAVASSIST level editor:

                 {url}

             Choose "Sign in with an email address", type this address, and a
             six-digit code will arrive here. There is no password. Signing in
             with a Google account of the same address works too.
             """);

        TempData["Msg"] = sent
            ? $"Invited {who} and emailed them."
            : mail.IsConfigured
                ? $"Invited {who}, but the email could not be sent — the error is in the console log."
                : $"Invited {who}. No mail settings, so tell them yourself: {url}";
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

    /// <summary>
    /// Δίνει ή αφαιρεί το δικαίωμα δημοσίευσης στο κοινό <c>levels/</c>.
    /// Χωριστό από την πρόσβαση: το να σχεδιάζεις αίθουσες δεν σημαίνει ότι
    /// γράφεις πάνω στα αρχεία που βλέπουν όλοι.
    /// </summary>
    [HttpPost("publish")]
    [ValidateAntiForgeryToken]
    public IActionResult Publish(string email, bool allow)
    {
        if (Guard() is { } stop) return stop;
        TempData["Msg"] = accounts.SetPublish(email, allow)
            ? (allow
                ? $"{AccountStore.Normalise(email)} can now publish to the shared levels."
                : $"{AccountStore.Normalise(email)} can no longer publish.")
            : "Could not change that address.";
        return RedirectToAction(nameof(Index));
    }

    /// <summary>
    /// Σβήνει τον λογαριασμό από τη λίστα. Ο φάκελός του μένει.
    /// Για αποκλεισμό υπάρχει η ανάκληση — ο σβησμένος ξαναεμφανίζεται ως
    /// νέο αίτημα την επόμενη φορά που θα συνδεθεί.
    /// </summary>
    [HttpPost("delete")]
    [ValidateAntiForgeryToken]
    public IActionResult Delete(string email)
    {
        if (Guard() is { } stop) return stop;
        TempData["Msg"] = accounts.Delete(email)
            ? $"Deleted {AccountStore.Normalise(email)} from the list. "
              + "Their levels folder is untouched."
            : "Could not delete that address.";
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
