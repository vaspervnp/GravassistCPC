using GravassistEditor.Services;
using Microsoft.AspNetCore.HttpOverrides;

// Level editor του GRAVASSIST — τοπικό εργαλείο, χωρίς εξαρτήσεις από internet.
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();

// ΠΙΣΩ ΑΠΟ REVERSE PROXY. Ο proxy τερματίζει το HTTPS και μιλά στον editor με
// σκέτο HTTP: χωρίς αυτό ο Kestrel βλέπει «http://localhost:5202» και χτίζει
// ΛΑΘΟΣ redirect_uri προς τη Google (http αντί https, λάθος host), οπότε η
// σύνδεση σκάει με redirect_uri_mismatch. Επηρεάζει και το cookie: με
// SameAsRequest θα έφευγε χωρίς τη σημαία Secure.
//
// Ο καθαρισμός των KnownNetworks/KnownProxies σημαίνει «εμπιστέψου τα
// X-Forwarded-* από οποιονδήποτε». Στέκει ΜΟΝΟ επειδή ο editor δεν είναι
// προσβάσιμος απευθείας — μόνο μέσω του proxy. Αν κάποτε ακούσει σε δημόσια
// διεύθυνση, αυτά τα δύο πρέπει να ξαναμπούν, αλλιώς ο καθένας δηλώνει ό,τι
// scheme και IP θέλει.
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor 
                             | ForwardedHeaders.XForwardedProto 
                             | ForwardedHeaders.XForwardedHost;
    
    // Allow headers from local proxy
    options.KnownNetworks.Clear();
    options.KnownProxies.Clear();
});
builder.Services.AddHttpContextAccessor();
// Πού είναι το repo (tools/, Makefile, levels/). Βρίσκεται ψάχνοντας προς
// τα πάνω — ο τρέχων κατάλογος ΔΕΝ είναι αξιόπιστος σε deployment.
builder.Services.AddSingleton<RepoLayout>();
// Ο προσωπικός φάκελος κάθε λογαριασμού μέσα στο levels/.
builder.Services.AddSingleton<UserWorkspace>();
// Ποιοι λογαριασμοί επιτρέπονται· ο διαχειριστής πάντα.
builder.Services.AddSingleton<AccountStore>();
// Σύνδεση με κωδικό σε email: ο αποστολέας και οι κωδικοί στον αέρα.
builder.Services.AddSingleton<Mailer>();
builder.Services.AddSingleton<LoginCodes>();
// SCOPED και όχι singleton: η ρίζα του εξαρτάται από ΠΟΙΟΣ ζητά. Ως singleton
// θα κλείδωνε τον πρώτο χρήστη που θα συνδεόταν και όλοι οι υπόλοιποι θα
// έγραφαν στα δικά του αρχεία.
builder.Services.AddScoped<LevelStore>();

// Η σύνδεση με Google είναι ΥΠΟΧΡΕΩΤΙΚΗ: χωρίς λογαριασμό δεν υπάρχει
// προσωπικός φάκελος, άρα δεν υπάρχει τίποτα να δείξει ο editor.
GoogleAuth.Add(builder);

var app = builder.Build();

// ΠΡΩΤΟ απ' όλα: διορθώνει scheme και host του αιτήματος πριν τα διαβάσει
// οτιδήποτε άλλο. Το Configure<ForwardedHeadersOptions> από μόνο του δεν
// κάνει τίποτα — χωρίς αυτή τη γραμμή οι επιλογές μένουν αχρησιμοποίητες.
app.UseForwardedHeaders();

// Προειδοποίηση αν ο κατάλογος τύπων ξέφυγε από το CHARS του tools/physics.py.
// Η διαδρομή ακολουθεί τη ρίζα του repo, όχι τον τρέχοντα κατάλογο.
var layout = app.Services.GetRequiredService<RepoLayout>();
var physics = app.Configuration["PhysicsPath"];
PhysicsCharsCheck.Run(
    string.IsNullOrWhiteSpace(physics)
        ? Path.Combine(layout.RepoRoot ?? app.Environment.ContentRootPath,
                       "tools", "physics.py")
        : Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, physics)),
    app.Logger);

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
}

// Το wwwroot/game/ σερβίρει το test run και τον έλεγχο ισοδυναμίας.
// ΧΩΡΙΣ CACHE για τα αρχεία του παιχνιδιού. Ο editor τα ξαναπαράγει σε κάθε
// build (make editor-data) και ο browser κρατούσε τα παλιά: δοκίμαζες μια
// αλλαγή, έβλεπες την προηγούμενη έκδοση, και το συμπέρασμα ήταν λάθος χωρίς
// κανένα σημάδι. Μια δοκιμή που δείχνει παλιά δεδομένα είναι χειρότερη από
// καθόλου δοκιμή.
app.UseStaticFiles(new StaticFileOptions
{
    OnPrepareResponse = ctx =>
    {
        if (ctx.Context.Request.Path.StartsWithSegments("/game"))
            ctx.Context.Response.Headers.CacheControl = "no-store, must-revalidate";
    },
});
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
// ΜΕΤΑ την εξουσιοδότηση: ξέρουμε ποιος είναι και κόβουμε όσους δεν έχουν
// εγκριθεί ακόμα, δείχνοντάς τους ΓΙΑΤΙ περιμένουν.
app.UseMiddleware<ApprovalGate>();

// Τα API endpoints ([ApiController] + [Route]) και μετά η σελίδα του editor.
app.MapControllers();
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
