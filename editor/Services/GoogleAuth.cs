using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.Google;
using Microsoft.AspNetCore.Authorization;

namespace GravassistEditor.Services;

/// <summary>
/// Σύνδεση με λογαριασμό Google.
///
/// ΤΑ ΜΥΣΤΙΚΑ ΕΡΧΟΝΤΑΙ ΑΠΟ ΜΕΤΑΒΛΗΤΕΣ ΠΕΡΙΒΑΛΛΟΝΤΟΣ και μόνο. Ούτε στο
/// appsettings.json ούτε σε αρχείο του repo: ό,τι μπει σε αρχείο εδώ,
/// commit-άρεται κάποια στιγμή κατά λάθος και μετά ζει για πάντα στο ιστορικό
/// του git.
///
/// Η ΣΥΝΔΕΣΗ ΕΙΝΑΙ ΥΠΟΧΡΕΩΤΙΚΗ. Κάθε λογαριασμός δουλεύει στον δικό του
/// υποφάκελο μέσα στο levels/, οπότε χωρίς λογαριασμό δεν υπάρχει καν φάκελος
/// να δείξει ο editor.
///
/// Αν λείπουν οι μεταβλητές, ο editor ΔΕΝ ΞΕΚΙΝΑ — με μήνυμα που λέει τι
/// λείπει. Το να ξεκινούσε ανοιχτός θα ήταν χειρότερο από το να μην ξεκινήσει
/// καθόλου: θα νόμιζες ότι είναι προστατευμένος.
/// </summary>
public static class GoogleAuth
{
    public const string IdVar = "gravassistGid";
    public const string SecretVar = "gravassistGscrt";

    /// <summary>Η διαδρομή επιστροφής που δηλώνεται και στο Google Cloud console.</summary>
    public const string CallbackPath = "/accounts/google";

    /// <summary>Ρυθμίστηκε η σύνδεση; Αν όχι, ο editor μένει ανοιχτός.</summary>
    public static bool IsConfigured(IConfiguration config) =>
        !string.IsNullOrWhiteSpace(config[IdVar]) &&
        !string.IsNullOrWhiteSpace(config[SecretVar]);

    /// <summary>Στήνει cookie + Google. Χωρίς μυστικά, σταματά το ξεκίνημα.</summary>
    public static void Add(WebApplicationBuilder builder)
    {
        var config = builder.Configuration;
        if (!IsConfigured(config))
        {
            throw new InvalidOperationException(
                $"Λείπουν τα μυστικά της σύνδεσης Google. Όρισε τις μεταβλητές "
                + $"περιβάλλοντος {IdVar} και {SecretVar}. Η διαδρομή "
                + $"επιστροφής στο Google Cloud console πρέπει να είναι "
                + $"<η διεύθυνσή σου>{CallbackPath}.");
        }

        builder.Services
            .AddAuthentication(o =>
            {
                o.DefaultScheme = CookieAuthenticationDefaults.AuthenticationScheme;
                o.DefaultChallengeScheme = GoogleDefaults.AuthenticationScheme;
            })
            .AddCookie(o =>
            {
                o.LoginPath = "/accounts/login";
                o.LogoutPath = "/accounts/logout";
                o.AccessDeniedPath = "/accounts/denied";
                // Ο editor είναι μακρόχρονη δουλειά: μια συνεδρία που λήγει
                // στη μέση ενός σχεδιασμού θα έχανε αποθηκευμένη δουλειά.
                o.ExpireTimeSpan = TimeSpan.FromDays(14);
                o.SlidingExpiration = true;
            })
            .AddGoogle(o =>
            {
                o.ClientId = config[IdVar]!;
                o.ClientSecret = config[SecretVar]!;
                o.CallbackPath = CallbackPath;
                o.SaveTokens = false;   // δεν καλούμε κανένα API της Google

                // ΤΗ ΣΤΙΓΜΗ ΤΗΣ ΣΥΝΔΕΣΗΣ, και μόνο τότε: όποιος έχει δικαίωμα
                // δημοσίευσης ξεκινά με τα κοινά levels/. Δουλεύει πάνω στο
                // κοινό σύνολο και το γράφει πίσω· ένα παλιό αντίγραφο θα
                // γύριζε πίσω τη δουλειά κάποιου άλλου στο επόμενο «Publish».
                o.Events.OnTicketReceived = ctx =>
                {
                    var services = ctx.HttpContext.RequestServices;
                    var accounts = services.GetRequiredService<AccountStore>();
                    var email = ctx.Principal?.FindFirstValue(ClaimTypes.Email);
                    if (ctx.Principal is null || !accounts.CanPublish(email))
                        return Task.CompletedTask;

                    var log = services.GetRequiredService<ILoggerFactory>()
                                      .CreateLogger(nameof(GoogleAuth));
                    try
                    {
                        var names = services.GetRequiredService<UserWorkspace>()
                                            .SyncOnSignIn(ctx.Principal);
                        if (names.Count > 0)
                            log.LogInformation(
                                "Sign-in sync: {Count} level(s) pulled from the shared folder ({Names}).",
                                names.Count, string.Join(", ", names));
                    }
                    catch (IOException ex)
                    {
                        // Η σύνδεση ΔΕΝ πρέπει να αποτύχει επειδή κόλλησε μια
                        // αντιγραφή αρχείων. Μπαίνει με ό,τι έχει ήδη.
                        log.LogWarning(ex, "Sign-in sync failed; continuing with the existing folder.");
                    }

                    return Task.CompletedTask;
                };
            });

        // ΟΛΑ κλειστά από προεπιλογή: ένας editor που γράφει αρχεία στον δίσκο
        // δεν πρέπει να έχει endpoint που ξέχασες να προστατέψεις.
        builder.Services.AddAuthorization(o =>
            o.FallbackPolicy = new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser()
                .Build());
    }
}
