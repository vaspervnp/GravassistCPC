using GravassistEditor.Services;

// Level editor του GRAVASSIST — τοπικό εργαλείο, χωρίς εξαρτήσεις από internet.
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
// Πρόσβαση στον φάκελο levels/ του repo.
builder.Services.AddSingleton<LevelStore>();

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

app.UseRouting();

// Τα API endpoints ([ApiController] + [Route]) και μετά η σελίδα του editor.
app.MapControllers();
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
