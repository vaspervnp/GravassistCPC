using System.Security.Claims;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.Google;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

/// <summary>
/// Σύνδεση και αποσύνδεση: με λογαριασμό Google ή με κωδικό σε email.
///
/// Η διαδρομή επιστροφής <c>/accounts/google</c> ΔΕΝ έχει action εδώ: την
/// χειρίζεται το ίδιο το middleware του Google (CallbackPath) πριν φτάσει
/// στο routing. Είναι δηλωμένη στο GoogleAuth και πρέπει να ταιριάζει με ό,τι
/// έχεις γράψει στο Google Cloud console.
///
/// ΚΑΙ ΟΙ ΔΥΟ ΔΡΟΜΟΙ ΚΑΤΑΛΗΓΟΥΝ ΣΤΟ ΙΔΙΟ COOKIE. Ο φραγμός έγκρισης, ο
/// προσωπικός φάκελος και τα δικαιώματα δημοσίευσης δεν ξέρουν καν ποιον
/// δρόμο διάλεξες — κοιτούν μόνο το claim του email.
/// </summary>
[AllowAnonymous]
[Route("accounts")]
public sealed class AccountsController(
    AccountStore accounts, LoginCodes codes, Mailer mail,
    ILogger<AccountsController> log) : Controller
{
    /// <summary>
    /// Η σελίδα σύνδεσης: κουμπί Google και, αν υπάρχει SMTP, φόρμα email.
    /// Εδώ καταλήγει κάθε ανώνυμος (LoginPath του cookie).
    /// </summary>
    [HttpGet("login")]
    public IActionResult Login(string? returnUrl = null, string? email = null)
    {
        ViewData["ReturnUrl"] = Local(returnUrl);
        ViewData["Mail"] = mail.IsConfigured;
        ViewData["Email"] = email ?? "";
        // Αν εκκρεμεί κωδικός γι' αυτή τη διεύθυνση, δείξε κατευθείαν το πεδίο
        // του κωδικού: ο χρήστης γύρισε από το γραμματοκιβώτιό του.
        ViewData["Stage"] = email is not null && codes.Pending(email) ? "code" : "start";
        return View();
    }

    /// <summary>Ξεκινά τη σύνδεση με Google· γυρίζει εκεί απ' όπου ήρθες.</summary>
    [HttpGet("google-login")]
    public IActionResult GoogleLogin(string? returnUrl = null) =>
        Challenge(new AuthenticationProperties { RedirectUri = Local(returnUrl) },
                  GoogleDefaults.AuthenticationScheme);

    /// <summary>Στέλνει εξαψήφιο κωδικό στη διεύθυνση.</summary>
    [HttpPost("code")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> SendCode(string email, string? returnUrl = null)
    {
        var to = AccountStore.Normalise(email);
        if (!mail.IsConfigured)
            return Back(returnUrl, to, "start", "Signing in by email is not available.");
        if (to.Length < 3 || !to.Contains('@') || to.Contains(' '))
            return Back(returnUrl, to, "start", "That does not look like an email address.");

        var ip = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "?";
        var (result, code) = codes.Issue(to, ip);

        if (result == CodeRequest.TooMany)
            return Back(returnUrl, to, "start",
                "Too many codes requested. Try again later.");

        if (result == CodeRequest.Sent)
        {
            var sent = await mail.SendAsync(to, "Your GRAVASSIST editor sign-in code",
                $"""
                 Your sign-in code is:

                     {code}

                 It is valid for {LoginCodes.Lifetime.TotalMinutes:0} minutes and can be
                 used once. If you did not ask for it, ignore this message — nobody
                 can sign in without it.
                 """);
            if (!sent)
                return Back(returnUrl, to, "start",
                    "The code could not be sent. Tell the administrator to check the mail settings.");
        }

        // ΙΔΙΑ ΑΠΑΝΤΗΣΗ είτε στάλθηκε τώρα είτε ίσχυε ήδη κωδικός: η διαφορά θα
        // έλεγε σε ξένο αν η διεύθυνση περιμένει σύνδεση.
        return Back(returnUrl, to, "code",
            $"If {to} can sign in, a code is on its way. It lasts "
            + $"{LoginCodes.Lifetime.TotalMinutes:0} minutes.");
    }

    /// <summary>Ελέγχει τον κωδικό και συνδέει.</summary>
    [HttpPost("verify")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Verify(string email, string code, string? returnUrl = null)
    {
        var to = AccountStore.Normalise(email);
        if (!codes.Verify(to, code))
            return Back(returnUrl, to, "code", "Wrong or expired code.");

        // Το ίδιο cookie με τη σύνδεση Google, με τα ίδια claims: από δω και
        // πέρα τίποτα στον editor δεν ξεχωρίζει τους δύο δρόμους.
        var identity = new ClaimsIdentity(
            [new Claim(ClaimTypes.Email, to), new Claim(ClaimTypes.Name, to),
             new Claim(ClaimTypes.NameIdentifier, to)],
            CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme,
                                      new ClaimsPrincipal(identity));

        // Άγνωστη διεύθυνση: μπαίνει στη λίστα αναμονής, όπως ακριβώς και με
        // Google. Ένα μοντέλο έγκρισης, όχι δύο.
        if (!accounts.IsAllowed(to)) accounts.RecordPending(to);
        log.LogInformation("Σύνδεση με κωδικό email: {Email}", to);
        return Redirect(Local(returnUrl));
    }

    [HttpGet("logout")]
    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        return Redirect("/");
    }

    /// <summary>Ποιος είναι συνδεδεμένος — το χρησιμοποιεί το UI.</summary>
    [HttpGet("me")]
    public IActionResult Me() => Ok(new
    {
        signedIn = User.Identity?.IsAuthenticated == true,
        name = User.Identity?.Name,
        email = User.FindFirstValue(ClaimTypes.Email),
    });

    /// <summary>
    /// Ο λογαριασμός συνδέθηκε αλλά δεν έχει εγκριθεί. Ξεχωριστή σελίδα και
    /// όχι σκέτο 403: ο χρήστης πρέπει να μάθει ότι ΠΕΡΙΜΕΝΕΙ, όχι ότι κάτι
    /// χάλασε — και να μπορεί να αποσυνδεθεί για να δοκιμάσει άλλο email.
    /// </summary>
    [HttpGet("pending")]
    public IActionResult Pending()
    {
        // Ασύνδετος ή ήδη εγκεκριμένος: δεν έχει τίποτα να περιμένει εδώ.
        if (User.Identity?.IsAuthenticated != true) return Redirect("/");
        var email = User.FindFirstValue(ClaimTypes.Email) ?? "";
        if (accounts.IsAllowed(email)) return Redirect("/");
        ViewData["Email"] = email;
        ViewData["Admin"] = accounts.AdminEmail;
        return View();
    }

    [HttpGet("denied")]
    public IActionResult Denied() =>
        Content("This Google account is not allowed to use the editor.",
                "text/plain");

    // ΜΟΝΟ τοπικές διαδρομές: αλλιώς ένας σύνδεσμος «login?returnUrl=…» θα
    // μπορούσε να στείλει τον χρήστη σε ξένο site μετά τη σύνδεση.
    private string Local(string? url) => Url.IsLocalUrl(url) ? url! : "/";

    private IActionResult Back(string? returnUrl, string email, string stage, string msg)
    {
        TempData["Msg"] = msg;
        TempData["Stage"] = stage;
        TempData["Email"] = email;
        return RedirectToAction(nameof(Login), new { returnUrl, email });
    }
}
