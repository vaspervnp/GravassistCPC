using System.Security.Claims;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.Google;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

/// <summary>
/// Σύνδεση και αποσύνδεση με λογαριασμό Google.
///
/// Η διαδρομή επιστροφής <c>/accounts/google</c> ΔΕΝ έχει action εδώ: την
/// χειρίζεται το ίδιο το middleware του Google (CallbackPath) πριν φτάσει
/// στο routing. Είναι δηλωμένη στο GoogleAuth και πρέπει να ταιριάζει με ό,τι
/// έχεις γράψει στο Google Cloud console.
/// </summary>
[AllowAnonymous]
[Route("accounts")]
public sealed class AccountsController : Controller
{
    /// <summary>Ξεκινά τη σύνδεση· γυρίζει εκεί απ' όπου ήρθες.</summary>
    [HttpGet("login")]
    public IActionResult Login(string? returnUrl = null)
    {
        // ΜΟΝΟ τοπικές διαδρομές: αλλιώς ένας σύνδεσμος «login?returnUrl=…»
        // θα μπορούσε να στείλει τον χρήστη σε ξένο site μετά τη σύνδεση.
        var target = Url.IsLocalUrl(returnUrl) ? returnUrl! : "/";
        return Challenge(new AuthenticationProperties { RedirectUri = target },
                         GoogleDefaults.AuthenticationScheme);
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

    [HttpGet("denied")]
    public IActionResult Denied() =>
        Content("This Google account is not allowed to use the editor.",
                "text/plain");
}
