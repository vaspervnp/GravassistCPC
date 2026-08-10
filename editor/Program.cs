using GravassistEditor.Services;

// Level editor του GRAVASSIST — τοπικό εργαλείο, χωρίς εξαρτήσεις από internet.
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
builder.Services.AddHttpContextAccessor();
// Ο προσωπικός φάκελος κάθε λογαριασμού μέσα στο levels/.
builder.Services.AddSingleton<UserWorkspace>();
// SCOPED και όχι singleton: η ρίζα του εξαρτάται από ΠΟΙΟΣ ζητά. Ως singleton
// θα κλείδωνε τον πρώτο χρήστη που θα συνδεόταν και όλοι οι υπόλοιποι θα
// έγραφαν στα δικά του αρχεία.
builder.Services.AddScoped<LevelStore>();

// Η σύνδεση με Google είναι ΥΠΟΧΡΕΩΤΙΚΗ: χωρίς λογαριασμό δεν υπάρχει
// προσωπικός φάκελος, άρα δεν υπάρχει τίποτα να δείξει ο editor.
GoogleAuth.Add(builder);

var app = builder.Build();

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
app.UseAuthentication();
app.UseAuthorization();

// Τα API endpoints ([ApiController] + [Route]) και μετά η σελίδα του editor.
app.MapControllers();
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
