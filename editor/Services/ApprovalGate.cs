using System.Security.Claims;

namespace GravassistEditor.Services;

/// <summary>
/// Κόβει τους συνδεδεμένους που ΔΕΝ έχουν εγκριθεί ακόμα.
///
/// Γιατί middleware και όχι πολιτική εξουσιοδότησης: η άρνηση εδώ δεν είναι
/// «δεν έχεις δικαίωμα» αλλά «περίμενε» — θέλει δική της σελίδα με εξήγηση,
/// και θέλει να ΚΑΤΑΓΡΑΨΕΙ το email ώστε να το δει ο διαχειριστής. Ένα σκέτο
/// 403 θα άφηνε τον χρήστη να κοιτάζει μια λευκή σελίδα και τον διαχειριστή
/// να μην ξέρει καν ότι κάποιος ζήτησε πρόσβαση.
///
/// Μπαίνει ΜΕΤΑ το UseAuthorization, ώστε να ξέρουμε ήδη ποιος είναι.
/// </summary>
public sealed class ApprovalGate(RequestDelegate next)
{
    // Ό,τι πρέπει να δουλεύει και για μη εγκεκριμένους: να δουν γιατί
    // περιμένουν, και να μπορούν να αποσυνδεθούν.
    private static readonly string[] Open =
        ["/accounts/logout", "/accounts/pending", "/accounts/me",
         "/accounts/denied", "/accounts/google", "/accounts/login",
         "/accounts/google-login", "/accounts/code", "/accounts/verify"];

    public async Task Invoke(HttpContext ctx, AccountStore accounts)
    {
        var path = ctx.Request.Path;
        if (ctx.User.Identity?.IsAuthenticated != true ||
            Open.Any(p => path.StartsWithSegments(p)))
        {
            await next(ctx);
            return;
        }

        var email = ctx.User.FindFirstValue(ClaimTypes.Email);
        if (accounts.IsAllowed(email))
        {
            await next(ctx);
            return;
        }

        accounts.RecordPending(email);
        ctx.Response.Redirect("/accounts/pending");
    }
}
