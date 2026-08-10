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
/// ΑΝ ΛΕΙΠΟΥΝ, Ο EDITOR ΤΡΕΧΕΙ ΟΠΩΣ ΠΡΙΝ, χωρίς σύνδεση και χωρίς έλεγχο
/// πρόσβασης. Είναι τοπικό εργαλείο που χρησιμοποιείται καθημερινά· να
/// σταματούσε να ανοίγει επειδή δεν έχεις ορίσει μεταβλητή θα ήταν χειρότερο
/// από το να μην έχει καθόλου λογαριασμούς. Μόλις οριστούν και οι δύο, η
/// σύνδεση γίνεται ΥΠΟΧΡΕΩΤΙΚΗ για όλες τις σελίδες και τα API.
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

    /// <summary>Στήνει cookie + Google, ΜΟΝΟ αν υπάρχουν τα μυστικά.</summary>
    public static bool Add(WebApplicationBuilder builder)
    {
        var config = builder.Configuration;
        if (!IsConfigured(config)) return false;

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
            });

        // ΟΛΑ κλειστά από προεπιλογή: ένας editor που γράφει αρχεία στον δίσκο
        // δεν πρέπει να έχει endpoint που ξέχασες να προστατέψεις.
        builder.Services.AddAuthorization(o =>
            o.FallbackPolicy = new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser()
                .Build());
        return true;
    }
}
