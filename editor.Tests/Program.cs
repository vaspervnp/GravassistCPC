using System.Security.Claims;
using GravassistEditor.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.FileProviders;

// Δουλεύει σε ΔΙΚΟ ΤΟΥ προσωρινό φάκελο: τα τεστ δεν αγγίζουν ποτέ
// τα πραγματικά levels/ του repo.
var root = Path.Combine(Path.GetTempPath(), "gravassist-ws-test");
if (Directory.Exists(root)) Directory.Delete(root, true);
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "room_1.txt"), "ένα");
File.WriteAllText(Path.Combine(root, "room_2.txt"), "δύο");
File.WriteAllText(Path.Combine(root, "regress.txt"), "τεστ");

var cfg = new ConfigurationBuilder()
    .AddInMemoryCollection(new Dictionary<string, string?> { ["LevelsPath"] = root })
    .Build();
var env = new Env();
var ws = new UserWorkspace(env, cfg);

ClaimsPrincipal U(params (string, string)[] cs) =>
    new(new ClaimsIdentity(cs.Select(c => new Claim(c.Item1, c.Item2)), "test"));

int fails = 0;
void Check(string name, bool ok, string detail = "")
{
    Console.WriteLine($"  {(ok ? "ΟΚ  " : "ΛΑΘΟΣ")} {name}{(detail.Length > 0 ? $"  [{detail}]" : "")}");
    if (!ok) fails++;
}

// --- καθαρισμός ονόματος
Check("email -> ασφαλές όνομα",
    UserWorkspace.KeyFor(U((ClaimTypes.Email, "Vasilis.P@example.com")))
        == "vasilis.p_at_example.com",
    UserWorkspace.KeyFor(U((ClaimTypes.Email, "Vasilis.P@example.com"))));
Check("τα «..» και τα «/» πετιούνται",
    UserWorkspace.KeyFor(U((ClaimTypes.Email, "../../etc/passwd")))
        == "etcpasswd",
    UserWorkspace.KeyFor(U((ClaimTypes.Email, "../../etc/passwd"))));
Check("χωρίς claims -> unknown", UserWorkspace.KeyFor(U()) == "unknown");

// --- φάκελος και σπορά
var dir = ws.PathFor(U((ClaimTypes.Email, "a@b.com")));
Check("ο φάκελος φτιάχτηκε μέσα στη ρίζα",
    dir == Path.Combine(root, "a_at_b.com") && Directory.Exists(dir), dir);
var seeded = Directory.GetFiles(dir).Select(Path.GetFileName).OrderBy(x => x).ToArray();
Check("αντιγράφηκαν ΟΛΑ τα κοινά αρχεία",
    string.Join(",", seeded) == "regress.txt,room_1.txt,room_2.txt",
    string.Join(",", seeded));
Check("το περιεχόμενο είναι το ίδιο",
    File.ReadAllText(Path.Combine(dir, "room_1.txt")) == "ένα");

// --- δεύτερη κλήση δεν ξανασπέρνει
File.WriteAllText(Path.Combine(dir, "room_1.txt"), "αλλαγμένο");
ws.PathFor(U((ClaimTypes.Email, "a@b.com")));
Check("δεύτερη σύνδεση ΔΕΝ σβήνει τη δουλειά σου",
    File.ReadAllText(Path.Combine(dir, "room_1.txt")) == "αλλαγμένο");

// --- δεύτερος χρήστης, χωριστός φάκελος
var dir2 = ws.PathFor(U((ClaimTypes.Email, "c@d.com")));
Check("άλλος λογαριασμός -> άλλος φάκελος", dir2 != dir && Directory.Exists(dir2));
Check("…και ΔΕΝ βλέπει τα αρχεία του πρώτου",
    File.ReadAllText(Path.Combine(dir2, "room_1.txt")) == "ένα");
Check("οι φάκελοι χρηστών δεν αντιγράφονται σε νέους",
    !Directory.Exists(Path.Combine(dir2, "a_at_b.com")));

Console.WriteLine(fails == 0 ? "ΟΛΑ ΣΩΣΤΑ" : $"{fails} ΑΠΟΤΥΧΙΕΣ");
Environment.Exit(fails);

sealed class Env : IWebHostEnvironment
{
    public string EnvironmentName { get; set; } = "Test";
    public string ApplicationName { get; set; } = "t";
    public string WebRootPath { get; set; } = "/tmp";
    public IFileProvider WebRootFileProvider { get; set; } = new NullFileProvider();
    public string ContentRootPath { get; set; } = "/tmp";
    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}
