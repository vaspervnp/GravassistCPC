using GravassistEditor.Services;

// Level editor του GRAVASSIST — τοπικό εργαλείο, χωρίς εξαρτήσεις από internet.
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllersWithViews();
// Πρόσβαση στον φάκελο levels/ του repo.
builder.Services.AddSingleton<LevelStore>();

var app = builder.Build();

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
