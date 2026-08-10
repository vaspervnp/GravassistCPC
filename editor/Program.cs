using GravassistEditor.Services;

// Level editor του GRAVASSIST — τοπικό εργαλείο, χωρίς εξαρτήσεις από internet.
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
// Πρόσβαση στον φάκελο levels/ του repo.
builder.Services.AddSingleton<LevelStore>();

// Σύνδεση με Google — ενεργή ΜΟΝΟ αν υπάρχουν τα μυστικά στο περιβάλλον.
// Δες Services/GoogleAuth.cs για το γιατί δεν είναι υποχρεωτική.
var authOn = GoogleAuth.Add(builder);

var app = builder.Build();

app.Logger.LogInformation(authOn
    ? "Google sign-in is ON; every page requires an account."
    : "Google sign-in is OFF: set {Id} and {Secret} to enable it.",
    GoogleAuth.IdVar, GoogleAuth.SecretVar);

// Προειδοποίηση αν ο κατάλογος τύπων ξέφυγε από το CHARS του tools/physics.py.
PhysicsCharsCheck.Run(
    Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath,
        builder.Configuration["PhysicsPath"] ?? "../tools/physics.py")),
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

if (authOn)
{
    app.UseAuthentication();
    app.UseAuthorization();
}

// Τα API endpoints ([ApiController] + [Route]) και μετά η σελίδα του editor.
app.MapControllers();
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
