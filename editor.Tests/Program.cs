using System.Linq;
using System.Security.Claims;
using GravassistEditor.Models;
using GravassistEditor.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Logging.Abstractions;

// Δουλεύει σε ΔΙΚΟ ΤΟΥ προσωρινό φάκελο: τα τεστ δεν αγγίζουν ποτέ
// τα πραγματικά levels/ του repo.
// Ο κοινός φάκελος λέγεται «levels» ΚΑΙ ΕΔΩ: η κεφαλίδα δείχνει το πραγματικό
// του όνομα, οπότε μια προσωρινή ρίζα με άλλο όνομα θα έλεγχε άλλο πράγμα.
var sandbox = Path.Combine(Path.GetTempPath(), "gravassist-ws-test");
if (Directory.Exists(sandbox)) Directory.Delete(sandbox, true);
var root = Path.Combine(sandbox, "levels");
Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, "room_1.txt"), "ένα");
File.WriteAllText(Path.Combine(root, "room_2.txt"), "δύο");
File.WriteAllText(Path.Combine(root, "regress.txt"), "τεστ");

var cfg = new ConfigurationBuilder()
    .AddInMemoryCollection(new Dictionary<string, string?> { ["LevelsPath"] = root })
    .Build();
var env = new Env();
UserWorkspace Workspace(IConfiguration c) =>
    new(new RepoLayout(env, c, new NullLogger<RepoLayout>()));
var ws = Workspace(cfg);

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

// --- το wwwroot βρίσκεται από όπου κι αν ξεκινήσει ο editor
// ΤΟ ΣΦΑΛΜΑ ΠΟΥ ΤΟ ΓΕΝΝΗΣΕ: το build output ΔΕΝ αντιγράφει το wwwroot, οπότε
// τρέχοντας το DLL από άλλον κατάλογο κάθε στατικό αρχείο γύριζε 404 — και το
// test run του browser ΕΙΝΑΙ στατικό αρχείο. Η σελίδα του editor δούλευε
// κανονικά (είναι μεταγλωττισμένη), οπότε το μόνο σημάδι ήταν ένα «HTTP ERROR
// 404» σε νέα καρτέλα.
var repoHere = RepoLayout.Find(Directory.GetCurrentDirectory())
               ?? RepoLayout.Find(AppContext.BaseDirectory);
Check("το wwwroot βρίσκεται από τη ρίζα του repo",
    RepoLayout.FindWebRoot(repoHere) is not null, repoHere ?? "(χωρίς ρίζα)");
Check("…και από τον κατάλογο του DLL, όπου δεν υπάρχει wwwroot",
    RepoLayout.FindWebRoot(AppContext.BaseDirectory) is not null,
    AppContext.BaseDirectory);
Check("…και ΔΕΝ βρίσκεται εκεί που δεν υπάρχει",
    RepoLayout.FindWebRoot(Path.GetTempPath()) is null);
// ΦΑΚΕΛΟΣ ΠΟΥ ΛΕΓΕΤΑΙ wwwroot ΑΛΛΑ ΔΕΝ ΕΙΝΑΙ Ο ΔΙΚΟΣ ΜΑΣ. Χωρίς αυτό, ένας
// έλεγχος «υπάρχει κατάλογος wwwroot;» περνούσε — και θα σέρβιρε τα λάθος
// αρχεία, ή κανένα, με τον editor να δείχνει μια χαρά.
var fakeWeb = Path.Combine(sandbox, "notours", "wwwroot");
Directory.CreateDirectory(fakeWeb);
Check("φάκελος wwwroot ΧΩΡΙΣ το game/play.html δεν μετράει",
    RepoLayout.FindWebRoot(Path.Combine(sandbox, "notours")) is null,
    fakeWeb);
Check("το σημάδι είναι το game/play.html, όχι το όνομα του φακέλου",
    File.Exists(Path.Combine(RepoLayout.FindWebRoot(repoHere)!, "game", "play.html")));

// --- η παλέτα υπάρχει ΚΑΙ σηκώνεται
// ΟΧΙ ΜΟΝΟ ΤΟ check_palette.py: εκείνο διαβάζει το αρχείο με regex. Εδώ ο
// κατάλογος ΧΤΙΖΕΤΑΙ — αν ο στατικός αρχικοποιητής σκάσει, η σελίδα του editor
// δεν δείχνει κανένα cell type και το regex δεν το μαθαίνει ποτέ.
Check("ο κατάλογος πλακιδίων χτίζεται", TileCatalog.All.Count > 40,
    $"{TileCatalog.All.Count} πλακίδια");
Check("κάθε πλακίδιο έχει δικό του χαρακτήρα",
    TileCatalog.All.Select(t => t.Symbol).Distinct().Count() == TileCatalog.All.Count);
Check("…και δικό του id για το <symbol> του πλέγματος",
    TileCatalog.All.Select(t => t.Id).Distinct().Count() == TileCatalog.All.Count);
Check("οι τέσσερις ζώνες βαρύτητας είναι μέσα",
    new[] { ':', '8', '4', '6' }.All(c => TileCatalog.All.Any(t => t.Symbol == c)),
    string.Join(",", TileCatalog.All.Where(t => t.Id.StartsWith("gravlock"))
                                    .Select(t => $"{t.Symbol}={t.Id}")));

// --- τι ΔΕΙΧΝΕΙ η κεφαλίδα
// Η απόλυτη διαδρομή ήταν μισή οθόνη μηχανήματος — και σε κοινό μηχάνημα
// έδειχνε και το home του διπλανού. Φαίνεται μόνο το /levels/<λογαριασμός>.
Check("η κεφαλίδα δείχνει /levels/<λογαριασμός>",
    ws.Display(dir) == "/levels/a_at_b.com",
    ws.Display(dir));
Check("…χωρίς ίχνος από την απόλυτη διαδρομή",
    !ws.Display(dir).Contains(Path.GetTempPath().TrimEnd(
        Path.DirectorySeparatorChar)));
Check("η ίδια η ρίζα δείχνεται σκέτη",
    ws.Display(ws.SharedRoot) == "/levels",
    ws.Display(ws.SharedRoot));
Check("φάκελος εκτός ρίζας δίνει ΜΟΝΟ το όνομά του",
    ws.Display(Path.Combine(Path.GetTempPath(), "alloy"))
        == "/levels/alloy",
    ws.Display(Path.Combine(Path.GetTempPath(), "alloy")));

// ------------------------------------------------------------ ρίζα του repo
// ΤΟ BUG ΠΟΥ ΕΦΤΑΣΕ ΣΕ DEPLOYMENT: η ρίζα υπολογιζόταν ως «τρέχων κατάλογος
// + ..», που ισχύει μόνο με dotnet run μέσα από το editor/. Σε πραγματικό
// deployment η διεργασία ξεκινά από το bin/, και ο editor έψαχνε το
// tools/genasm.py εκεί μέσα.
var fake = Path.Combine(Path.GetTempPath(), "gravassist-repo-test");
if (Directory.Exists(fake)) Directory.Delete(fake, true);
Directory.CreateDirectory(Path.Combine(fake, "tools"));
Directory.CreateDirectory(Path.Combine(fake, "editor", "bin", "Debug", "net10.0"));
File.WriteAllText(Path.Combine(fake, "Makefile"), "all:");
File.WriteAllText(Path.Combine(fake, "tools", "genasm.py"), "# ...");

Check("η ρίζα αναγνωρίζεται", RepoLayout.Looks(fake));
Check("ένας τυχαίος κατάλογος ΔΕΝ περνά για ρίζα",
    !RepoLayout.Looks(Path.GetTempPath()));
Check("βρίσκεται από την ίδια τη ρίζα", RepoLayout.Find(fake) == fake);
Check("βρίσκεται ΑΠΟ ΜΕΣΑ ΑΠΟ ΤΟ bin/ — η περίπτωση του deployment",
    RepoLayout.Find(Path.Combine(fake, "editor", "bin", "Debug", "net10.0")) == fake,
    RepoLayout.Find(Path.Combine(fake, "editor", "bin", "Debug", "net10.0")) ?? "null");
Check("χωρίς ρίζα από πάνω -> null",
    RepoLayout.Find(Path.GetTempPath()) is null || !Directory.Exists(
        Path.Combine(Path.GetTempPath(), "Makefile")));
Check("κενή αφετηρία -> null", RepoLayout.Find(null) is null && RepoLayout.Find("") is null);

// Το Makefile χωρίς το tools/genasm.py δεν αρκεί: θέλουμε ΚΑΙ ΤΑ ΔΥΟ, αλλιώς
// ένας οποιοσδήποτε φάκελος με Makefile θα περνούσε για ρίζα.
var half = Path.Combine(Path.GetTempPath(), "gravassist-half");
if (Directory.Exists(half)) Directory.Delete(half, true);
Directory.CreateDirectory(half);
File.WriteAllText(Path.Combine(half, "Makefile"), "all:");
Check("μόνο Makefile δεν αρκεί", !RepoLayout.Looks(half));

// --- οι πίστες ακολουθούν τη ρίζα όταν δεν έχουν οριστεί ρητά
var auto = new RepoLayout(new Env { ContentRootPath = Path.Combine(fake, "editor") },
    new ConfigurationBuilder().Build(), new NullLogger<RepoLayout>());
Check("χωρίς ρύθμιση, τα levels βγαίνουν από τη ρίζα",
    auto.RepoRoot == fake && auto.LevelsRoot == Path.Combine(fake, "levels"),
    auto.LevelsRoot);

var told = new RepoLayout(new Env { ContentRootPath = Path.Combine(fake, "editor") },
    new ConfigurationBuilder().AddInMemoryCollection(
        new Dictionary<string, string?> { ["gravassistRepo"] = fake }).Build(),
    new NullLogger<RepoLayout>());
Check("το gravassistRepo παρακάμπτει την αναζήτηση", told.RepoRoot == fake);

// ---------------------------------------------------------------- λογαριασμοί
// Η λίστα εγκεκριμένων είναι ο ΜΟΝΟΣ φραγμός ανάμεσα σε «συνδέθηκα με Google»
// και «γράφω αρχεία στον server». Δεν ελέγχεται με το μάτι.
var adminMail = "boss@example.com";
var accRoot = Path.Combine(Path.GetTempPath(), "gravassist-acc-test");
if (Directory.Exists(accRoot)) Directory.Delete(accRoot, true);
Directory.CreateDirectory(accRoot);
var accEnv = new Env { ContentRootPath = accRoot };
var accCfg = new ConfigurationBuilder()
    .AddInMemoryCollection(new Dictionary<string, string?>
        { ["gravassistGadmin"] = "  BOSS@Example.com "  })
    .Build();
var acc = new AccountStore(accEnv, accCfg);

Check("ο διαχειριστής επιτρέπεται πάντα, χωρίς εγγραφή",
    acc.IsAllowed("Boss@Example.COM") && acc.IsAdmin(adminMail));
Check("άγνωστος λογαριασμός ΔΕΝ επιτρέπεται", !acc.IsAllowed("x@y.com"));
Check("κενό email ΔΕΝ επιτρέπεται", !acc.IsAllowed("") && !acc.IsAllowed(null));

acc.RecordPending("Pending@X.com");
Check("όποιος ζητήσει καταγράφεται…",
    acc.All().Any(a => a.Email == "pending@x.com" && !a.Allowed));
Check("…αλλά ΔΕΝ αποκτά πρόσβαση", !acc.IsAllowed("pending@x.com"));

Check("έγκριση δίνει πρόσβαση",
    acc.Approve("PENDING@x.com") && acc.IsAllowed("pending@x.com"));
acc.RecordPending("pending@x.com");
Check("νέα σύνδεση ΔΕΝ ξαναρίχνει εγκεκριμένον σε αναμονή",
    acc.IsAllowed("pending@x.com"));

Check("πρόσκληση δίνει πρόσβαση κατευθείαν",
    acc.Invite("friend@x.com") && acc.IsAllowed("friend@x.com"));
Check("σκουπίδι δεν μπαίνει στη λίστα",
    !acc.Invite("όχι-email") && !acc.Invite("a b@c.com") && !acc.Invite(""));

Check("η ανάκληση κόβει την πρόσβαση",
    acc.Revoke("friend@x.com") && !acc.IsAllowed("friend@x.com"));
Check("ο διαχειριστής ΔΕΝ ανακαλείται",
    !acc.Revoke(adminMail) && acc.IsAllowed(adminMail));

Check("όσοι περιμένουν έρχονται πρώτοι στη λίστα",
    acc.All().First().Allowed == false);

// --- επιβίωση σε restart
var acc2 = new AccountStore(accEnv, accCfg);
Check("η λίστα διαβάζεται ξανά μετά από restart",
    acc2.IsAllowed("pending@x.com") && !acc2.IsAllowed("friend@x.com"));

// --- χαλασμένο αρχείο: ο editor πρέπει να σηκώνεται
File.WriteAllText(Path.Combine(accRoot, "App_Data", "accounts.json"), "{όχι json");
var acc3 = new AccountStore(accEnv, accCfg);
Check("χαλασμένο accounts.json δεν ρίχνει τον editor",
    acc3.IsAllowed(adminMail) && !acc3.IsAllowed("pending@x.com"));

// --- διαγραφή: καθάρισμα λίστας, ΟΧΙ αποκλεισμός
var del = new AccountStore(accEnv, accCfg);
del.Invite("gone@x.com");
Check("η διαγραφή βγάζει τον λογαριασμό",
    del.Delete("GONE@x.com") && !del.IsAllowed("gone@x.com")
    && del.All().All(a => a.Email != "gone@x.com"));
Check("δεύτερη διαγραφή δεν βρίσκει τίποτα", !del.Delete("gone@x.com"));
Check("ο διαχειριστής ΔΕΝ σβήνεται",
    !del.Delete(adminMail) && del.IsAllowed(adminMail));
Check("κενό email δεν σβήνει τίποτα", !del.Delete("") && !del.Delete(null));

// Η ΚΡΙΣΙΜΗ ΔΙΑΦΟΡΑ: ο ανακληθείς μένει κομμένος αν ξαναζητήσει, ο
// σβησμένος επανεμφανίζεται ως νέο αίτημα.
del.Invite("blocked@x.com");
del.Revoke("blocked@x.com");
del.RecordPending("blocked@x.com");
Check("ο ανακληθείς μένει «revoked», δεν ξαναγίνεται απλό αίτημα",
    del.All().Single(a => a.Email == "blocked@x.com").Note == "revoked");

del.Invite("forgotten@x.com");
del.Delete("forgotten@x.com");
del.RecordPending("forgotten@x.com");
Check("ο σβησμένος ξαναεμφανίζεται ως νέο αίτημα",
    del.All().Single(a => a.Email == "forgotten@x.com") is { Allowed: false, Note: "asked" });

var del2 = new AccountStore(accEnv, accCfg);
Check("η διαγραφή επιβιώνει restart", del2.All().All(a => a.Email != "gone@x.com"));

// ------------------------------------------------------------------- ο φραγμός
// Ο ApprovalGate είναι που εμποδίζει ΣΤΗΝ ΠΡΑΞΗ. Αν περάσει το αίτημα, το
// επόμενο βήμα φτιάχνει φάκελο στα levels/ — γι' αυτό ο ψεύτικος «επόμενος»
// εδώ κάνει ακριβώς αυτό.
var gate = new AccountStore(accEnv, accCfg);
gate.Invite("ok@x.com");

async Task<(bool passed, int status, string? go)> Ask(string path, string? email)
{
    var passed = false;
    var mw = new ApprovalGate(c =>
    {
        passed = true;
        if (email is not null) ws.PathFor(U((ClaimTypes.Email, email)));   // ό,τι κάνει ο editor
        return Task.CompletedTask;
    });
    var ctx = new DefaultHttpContext();
    ctx.Request.Path = path;
    if (email is not null)
        ctx.User = new ClaimsPrincipal(
            new ClaimsIdentity([new Claim(ClaimTypes.Email, email)], "test"));
    await mw.Invoke(ctx, gate);
    return (passed, ctx.Response.StatusCode, ctx.Response.Headers.Location);
}

var r = await Ask("/", "blocked@x.com");
Check("ο μη εγκεκριμένος ΔΕΝ περνά", !r.passed);
Check("…και στέλνεται στη σελίδα αναμονής", r.go == "/accounts/pending", r.go ?? "-");
Check("…ΔΕΝ του φτιάχνεται φάκελος στα levels/",
    !Directory.Exists(Path.Combine(root, "blocked_at_x.com")));
Check("…αλλά ο διαχειριστής βλέπει το αίτημά του",
    gate.All().Any(a => a.Email == "blocked@x.com" && !a.Allowed));

Check("ο εγκεκριμένος περνά", (await Ask("/", "ok@x.com")).passed);
Check("ο διαχειριστής περνά", (await Ask("/admin", adminMail)).passed);
Check("η αποσύνδεση δουλεύει και για μη εγκεκριμένον",
    (await Ask("/accounts/logout", "blocked@x.com")).passed);
Check("η σελίδα αναμονής δεν στέλνει στον εαυτό της",
    (await Ask("/accounts/pending", "blocked@x.com")).passed);
Check("ο ασύνδετος περνά (τον πιάνει η σύνδεση, όχι ο φραγμός)",
    (await Ask("/", null)).passed);

// ------------------------------------------------------------- δημοσίευση
// Η δημοσίευση γράφει πάνω στα ΚΟΙΝΑ αρχεία — αυτά που σπέρνουν κάθε νέο
// λογαριασμό. Το ποιος επιτρέπεται δεν κρίνεται από το αν φαίνεται το κουμπί.
var pub = new AccountStore(accEnv, accCfg);
Check("κανείς δεν δημοσιεύει από προεπιλογή",
    !pub.CanPublish("someone@x.com"));
pub.Invite("writer@x.com");
Check("ούτε καν ο εγκεκριμένος", !pub.CanPublish("writer@x.com"));
Check("ο διαχειριστής δημοσιεύει πάντα", pub.CanPublish(adminMail));
Check("ο διαχειριστής δεν έχει σημαία να αλλάξει",
    !pub.SetPublish(adminMail, false) && pub.CanPublish(adminMail));
Check("σε άγνωστο λογαριασμό δεν δίνεται",
    !pub.SetPublish("ghost@x.com", true) && !pub.CanPublish("ghost@x.com"));

Check("ο διαχειριστής το δίνει",
    pub.SetPublish("WRITER@x.com", true) && pub.CanPublish("writer@x.com"));
Check("…και το παίρνει πίσω",
    pub.SetPublish("writer@x.com", false) && !pub.CanPublish("writer@x.com"));

pub.SetPublish("writer@x.com", true);
pub.Revoke("writer@x.com");
Check("ο ανακληθείς ΔΕΝ δημοσιεύει, ό,τι κι αν λέει η σημαία του",
    !pub.CanPublish("writer@x.com"));
Check("η επανέγκριση δεν αλλάζει σιωπηλά τη σημαία",
    pub.Approve("writer@x.com") && pub.CanPublish("writer@x.com"));

var pub2 = new AccountStore(accEnv, accCfg);
Check("η σημαία επιβιώνει restart", pub2.CanPublish("writer@x.com"));

// --- αντιγραφή προς τα κοινά και πίσω
var shared = Path.Combine(Path.GetTempPath(), "gravassist-pub-test");
if (Directory.Exists(shared)) Directory.Delete(shared, true);
Directory.CreateDirectory(shared);
File.WriteAllText(Path.Combine(shared, "room_1.txt"), "κοινό ένα");
File.WriteAllText(Path.Combine(shared, "room_9.txt"), "μόνο κοινό");
var cfg2 = new ConfigurationBuilder()
    .AddInMemoryCollection(new Dictionary<string, string?> { ["LevelsPath"] = shared })
    .Build();
var ws2 = Workspace(cfg2);
var mine = ws2.PathFor(U((ClaimTypes.Email, "w@x.com")));

File.WriteAllText(Path.Combine(mine, "room_1.txt"), "δικό μου ένα");   // αλλαγμένο
File.WriteAllText(Path.Combine(mine, "room_7.txt"), "καινούριο");      // νέο
File.WriteAllBytes(Path.Combine(mine, "gravassist.dsk"), [1, 2, 3]);   // ΟΧΙ .txt

var prev = ws2.PublishPreview(mine).OrderBy(c => c.Name).ToList();
Check("η προεπισκόπηση λέει ΤΙ θα αλλάξει, χωρίς να γράψει",
    string.Join(",", prev.Select(c => $"{c.Name}:{c.Kind}"))
        == "room_1.txt:changed,room_7.txt:new"
    && File.ReadAllText(Path.Combine(shared, "room_1.txt")) == "κοινό ένα",
    string.Join(",", prev.Select(c => $"{c.Name}:{c.Kind}")));

var wrote = ws2.Publish(mine);
Check("η δημοσίευση γράφει ακριβώς αυτά", string.Join(",", wrote.OrderBy(x => x))
    == "room_1.txt,room_7.txt");
Check("…και το κοινό πήρε το περιεχόμενό μου",
    File.ReadAllText(Path.Combine(shared, "room_1.txt")) == "δικό μου ένα");
Check("η δισκέτα ΔΕΝ δημοσιεύεται",
    !File.Exists(Path.Combine(shared, "gravassist.dsk")));
Check("αρχείο που έχει μόνο το κοινό ΔΕΝ σβήνεται",
    File.Exists(Path.Combine(shared, "room_9.txt")));
Check("δεύτερη δημοσίευση δεν έχει τίποτα να κάνει", ws2.Publish(mine).Count == 0);

// --- το αντίστροφο: τράβηγμα
File.WriteAllText(Path.Combine(shared, "room_1.txt"), "άλλαξε αλλού");   // αλλαγμένο
File.WriteAllText(Path.Combine(shared, "room_4.txt"), "καινούρια κοινή"); // νέο για μένα
File.WriteAllText(Path.Combine(mine, "room_8.txt"), "μόνο δικό μου");
var pulled = ws2.Pull(mine);
Check("το τράβηγμα φέρνει ό,τι διαφέρει",
    string.Join(",", pulled.OrderBy(x => x)) == "room_1.txt,room_4.txt",
    string.Join(",", pulled));
Check("…μαζί με ό,τι δεν είχα καθόλου",
    File.ReadAllText(Path.Combine(mine, "room_4.txt")) == "καινούρια κοινή");
Check("…πατώντας το δικό μου",
    File.ReadAllText(Path.Combine(mine, "room_1.txt")) == "άλλαξε αλλού");
Check("…χωρίς να σβήνει ό,τι έχω μόνο εγώ",
    File.Exists(Path.Combine(mine, "room_8.txt")));
Check("δεύτερο τράβηγμα δεν έχει τίποτα να κάνει", ws2.Pull(mine).Count == 0);

// ------------------------------------------------ κωδικοί σύνδεσης με email
// Ο κωδικός ΕΙΝΑΙ το διαπιστευτήριο — δεν υπάρχει password από πίσω. Ό,τι
// αφήσουμε χαλαρό εδώ είναι ανοιχτή πόρτα, όχι ταλαιπωρία.
var codes = new LoginCodes(new NullLogger<LoginCodes>());

var (r1, c1) = codes.Issue("a@x.com", "10.0.0.1");
Check("ο κωδικός φτιάχνεται", r1 == CodeRequest.Sent && c1 is { Length: 6 }, c1 ?? "-");
Check("είναι έξι ψηφία", c1!.All(char.IsAsciiDigit));
Check("εκκρεμεί", codes.Pending("A@X.COM"));

Check("λάθος κωδικός δεν περνά", !codes.Verify("a@x.com", "000000") || c1 == "000000");
Check("άλλη διεύθυνση δεν περνά με τον ίδιο κωδικό", !codes.Verify("b@x.com", c1));
Check("ο σωστός περνά", codes.Verify("A@X.com", c1));
Check("…και καταναλώνεται — δεν ξαναδουλεύει", !codes.Verify("a@x.com", c1));
Check("…και δεν εκκρεμεί πια", !codes.Pending("a@x.com"));

// --- πέντε λάθος προσπάθειες καίνε τον κωδικό
var (_, c2) = codes.Issue("burn@x.com", "10.0.0.2");
var wrong = c2 == "111111" ? "222222" : "111111";
for (var i = 0; i < 5; i++) codes.Verify("burn@x.com", wrong);
Check("μετά από 5 λάθος, ούτε ο σωστός δεν περνά", !codes.Verify("burn@x.com", c2));

// --- φραγμοί: η φόρμα δεν γίνεται μηχανή αποστολής email
// ΠΡΟΣΟΧΗ σε ποιον έλεγχο: η αναμονή μετριέται από τον ΕΝΕΡΓΟ κωδικό, οπότε
// πρέπει να υπάρχει ένας που δεν έχει καταναλωθεί.
Check("πρώτος κωδικός για καθαρή διεύθυνση",
    codes.Issue("cool@x.com", "10.0.0.1").Result == CodeRequest.Sent);
Check("δεύτερος αμέσως μετά -> TooSoon",
    codes.Issue("COOL@x.com", "10.0.0.1").Result == CodeRequest.TooSoon);
Check("μετά από επιτυχή σύνδεση δεν κρατάει αναμονή",
    codes.Verify("cool@x.com", "000000") == false);

var perEmail = new LoginCodes(new NullLogger<LoginCodes>());
var results = new List<CodeRequest>();
for (var i = 0; i < 7; i++)
    results.Add(perEmail.Issue($"spam{i}@x.com", "10.0.0.3").Result);
Check("όριο ανά IP: οι πρώτες 10 περνούν, μετά όχι",
    results.Take(7).All(x => x == CodeRequest.Sent));
for (var i = 7; i < 12; i++) results.Add(perEmail.Issue($"spam{i}@x.com", "10.0.0.3").Result);
Check("…και η 11η από την ίδια IP κόβεται",
    results[10] == CodeRequest.TooMany && results[11] == CodeRequest.TooMany,
    string.Join(",", results.Skip(9)));
Check("άλλη IP δεν επηρεάζεται",
    perEmail.Issue("other@x.com", "10.0.0.9").Result == CodeRequest.Sent);

// --- δύο κωδικοί δεν είναι ποτέ ο ίδιος (πρακτικά)
var seen = new HashSet<string>();
var many = new LoginCodes(new NullLogger<LoginCodes>());
for (var i = 0; i < 50; i++)
{
    var (_, c) = many.Issue($"u{i}@x.com", $"10.1.0.{i}");
    if (c is not null) seen.Add(c);
}
Check("οι κωδικοί δεν επαναλαμβάνονται", seen.Count >= 45, $"{seen.Count} διαφορετικοί");

// -------------------------------------------------------- εξαγωγή / εισαγωγή
// ΤΟ ZIP ΕΙΝΑΙ ΞΕΝΟ ΑΡΧΕΙΟ. Ό,τι έρθει από έξω και καταλήγει σε ΔΙΑΔΡΟΜΗ
// ΑΡΧΕΙΟΥ ελέγχεται εδώ, όχι με το μάτι.
var arc = new LevelArchive();
var zdir = Path.Combine(Path.GetTempPath(), "gravassist-zip-test");
if (Directory.Exists(zdir)) Directory.Delete(zdir, true);
Directory.CreateDirectory(zdir);

string Level(string mark)
{
    var rows = new List<string> { new string('#', 40) };
    for (var i = 0; i < 22; i++) rows.Add("#" + new string('.', 38) + "#");
    rows.Add(new string('#', 40));
    var body = rows[21].ToCharArray();
    body[2] = '@';
    rows[21] = new string(body);
    return $";  {mark}\n" + string.Join("\n", rows) + "\ngravity 0\n";
}

File.WriteAllText(Path.Combine(zdir, "room_1.txt"), Level("ena"));
File.WriteAllText(Path.Combine(zdir, "room_2.txt"), Level("dyo"));
File.WriteAllBytes(Path.Combine(zdir, "gravassist.dsk"), new byte[] { 1, 2, 3 });

var zipBytes = arc.Export(zdir);
using (var z = new System.IO.Compression.ZipArchive(new MemoryStream(zipBytes)))
{
    var names = z.Entries.Select(e => e.FullName).OrderBy(x => x).ToList();
    Check("η εξαγωγή παίρνει ΜΟΝΟ τα .txt",
          string.Join(",", names) == "room_1.txt,room_2.txt", string.Join(",", names));
}

byte[] MakeZip(params (string Name, string Body)[] items)
{
    using var ms = new MemoryStream();
    using (var z = new System.IO.Compression.ZipArchive(
               ms, System.IO.Compression.ZipArchiveMode.Create, true))
        foreach (var (n, b) in items)
        {
            using var w = new StreamWriter(z.CreateEntry(n).Open());
            w.Write(b);
        }

    return ms.ToArray();
}

// --- ΤΟ ΚΡΙΣΙΜΟ: zip slip
var evil = Path.Combine(Path.GetTempPath(), "gravassist-pwned.txt");
if (File.Exists(evil)) File.Delete(evil);
var plan = arc.Import(new MemoryStream(
    MakeZip(("../../../../../../tmp/gravassist-pwned.txt", Level("kako")))), zdir);
Check("εγγραφή με διαδρομή ΔΕΝ γράφει έξω από τον φάκελο", !File.Exists(evil));
Check("…και αναφέρεται ως παραλειφθείσα",
      plan.Any(e => e.Kind == "skipped"), plan[0].Kind + ": " + plan[0].Detail);

// --- κανονική εισαγωγή
var round = arc.Import(new MemoryStream(zipBytes), zdir);
Check("το ίδιο zip πάνω στα ίδια αρχεία δεν αλλάζει τίποτα",
      round.All(e => e.Kind == "same"), string.Join(",", round.Select(e => e.Kind)));

var plan2 = arc.Import(new MemoryStream(
    MakeZip(("room_2.txt", Level("allagmeno")), ("room_7.txt", Level("kainourio")))), zdir);
Check("νέο αρχείο γράφεται", File.Exists(Path.Combine(zdir, "room_7.txt")));
Check("…και το αλλαγμένο ενημερώνεται",
      File.ReadAllText(Path.Combine(zdir, "room_2.txt")).Contains("allagmeno"));
Check("…με σωστό χαρακτηρισμό",
      plan2.Single(e => e.Name == "room_7.txt").Kind == "new"
      && plan2.Single(e => e.Name == "room_2.txt").Kind == "changed");

// --- ΟΛΑ Ή ΤΙΠΟΤΑ: μια άκυρη πίστα δεν αφήνει μισή εισαγωγή
var before = File.ReadAllText(Path.Combine(zdir, "room_1.txt"));
var bad = arc.Import(new MemoryStream(
    MakeZip(("room_1.txt", Level("nea")), ("room_8.txt", ";σκουπίδια\nxxx\n"))), zdir);
Check("άκυρη πίστα -> ΚΑΜΙΑ δεν γράφεται",
      File.ReadAllText(Path.Combine(zdir, "room_1.txt")) == before
      && !File.Exists(Path.Combine(zdir, "room_8.txt")));
Check("…και λέει ποια φταίει",
      bad.Any(e => e.Kind == "error" && e.Name == "room_8.txt"),
      string.Join(",", bad.Select(e => e.Name + ":" + e.Kind)));

// --- σκουπίδια αντί για zip
var junk = arc.Import(new MemoryStream("δεν είμαι zip"u8.ToArray()), zdir);
Check("αρχείο που δεν είναι zip απορρίπτεται καθαρά",
      junk.Count == 1 && junk[0].Kind == "error", junk[0].Detail);

// --- ό,τι δεν είναι .txt αγνοείται, δεν ρίχνει την εισαγωγή
var mixed = arc.Import(new MemoryStream(
    MakeZip(("readme.md", "x"), ("room_3.txt", Level("tria")))), zdir);
Check("μη-.txt αγνοείται και η υπόλοιπη εισαγωγή προχωρά",
      File.Exists(Path.Combine(zdir, "room_3.txt"))
      && mixed.Any(e => e.Name == "readme.md" && e.Kind == "skipped"));

// ==================================================================== πυργίσκοι
//
// Ο πυργίσκος είναι το μόνο καλωδιωμένο αντικείμενο με ΤΡΕΙΣ αριθμούς, οπότε
// έχει δική του γραμμή και δικό του γράφο. Ό,τι ελέγχεται εδώ είναι ακριβώς τα
// σημεία όπου αυτό διαφέρει από τα υπόλοιπα είδη.

Console.WriteLine("--- πυργίσκοι");

// Πίστα με πυργίσκους σε δοσμένες θέσεις, πάνω στο ίδιο άδειο δωμάτιο.
string TurretLevel(params (int Col, int Row, char Sym)[] cells)
{
    var rows = new List<string> { new('#', 40) };
    for (var i = 0; i < 22; i++) rows.Add("#" + new string('.', 38) + "#");
    rows.Add(new string('#', 40));
    foreach (var (c, r, s) in cells)
    {
        var line = rows[r].ToCharArray();
        line[c] = s;
        rows[r] = new string(line);
    }

    return "; turrets\n" + string.Join("\n", rows) + "\ngravity 0\n";
}

var tOne = TurretGraph.ParseLines(["turret 10 16 4 2 3"]).Single();
Check("η γραμμή διαβάζεται με τους τρεις αριθμούς",
      tOne is { Col: 10, Row: 16, Channel: 4, Reload: 2, Auto: 3 }, tOne.ToString());

var tShort = TurretGraph.ParseLines(["turret 10 16 4"]).Single();
Check("χωρίς χρόνους ισχύουν οι προεπιλογές — όπως στο physics.py",
      tShort is { Channel: 4, Auto: 0 } && tShort.Reload == TurretGraph.DefaultReload,
      tShort.ToString());

// Η ΓΡΑΜΜΗ ΔΕΝ ΑΝΗΚΕΙ ΣΤΟΝ AttrGraph. Αν του ανήκε, το SetAttrLinks θα την
// έσβηνε και θα την ξανάγραφε ως «turret c r v» — δηλαδή χωρίς τους χρόνους.
//
// ΜΕ ΤΗ ΣΥΝΤΟΜΗ ΜΟΡΦΗ, και όχι με την πλήρη: εκείνη έχει πέντε αριθμούς και δεν
// ταιριάζει στο σχήμα της καλωδίωσης ούτως ή άλλως, οπότε δεν αποδεικνύει
// τίποτα. Η «turret 10 16 4» είναι ακριβώς όσο μοιάζει με «gate 10 16 4», και
// είναι ΝΟΜΙΜΗ γραμμή — έτσι γράφονταν οι πυργίσκοι πριν αποκτήσουν χρόνους.
foreach (var line in new[] { "turret 10 16 4", "turret 10 16 4 2 3" })
{
    Check($"ο AttrGraph ΔΕΝ αναγνωρίζει «{line}»", !AttrGraph.IsAttrLine(line));
    Check("…ούτε τη διαβάζει ως καλωδίωση", AttrGraph.ParseLines([line]).Count == 0);

    var keep = LevelDocument.Parse(TurretLevel((10, 16, 'I')));
    keep.Footer.Add(line);
    keep.SetAttrLinks([new AttrLink("gate", 5, 5, 1)]);
    Check("…και το SetAttrLinks την αφήνει άθικτη",
          keep.Footer.Contains(line), string.Join(" | ", keep.Footer));
}

// ΜΙΑ ΓΡΑΜΜΗ ΑΝΑ ΚΕΛΙ. Το turret_arg του μοντέλου έχει κλειδί το κελί και δεν
// απλώνεται στην ομάδα: με μία μόνο γραμμή, ο δεύτερος από δύο κολλητούς
// πυργίσκους θα κρατούσε το κανάλι αλλά θα έπαιρνε τους προεπιλεγμένους χρόνους.
var pair = LevelDocument.Parse(TurretLevel((10, 16, 'I'), (10, 17, 'I')));
Check("δύο κολλητοί πυργίσκοι είναι ΜΙΑ ομάδα",
      pair.TurretGroups().Single().Cells.Count == 2);
pair.SetTurretLinks([new TurretLink(10, 16, 4, 2, 3)]);
Check("…και γράφονται ΔΥΟ γραμμές, μία ανά κελί",
      pair.Footer.Count(TurretGraph.IsTurretLine) == 2
      && pair.Footer.Contains("turret 10 16 4 2 3")
      && pair.Footer.Contains("turret 10 17 4 2 3"),
      string.Join(" | ", pair.Footer.Where(TurretGraph.IsTurretLine)));

// Οι δύο άξονες είναι ΔΙΑΦΟΡΕΤΙΚΟΙ χαρακτήρες, άρα διαφορετικά αντικείμενα
// ακόμα κι όταν ακουμπάνε — ακριβώς όπως τα κρίνει το _groups_of του physics.py.
var axes = LevelDocument.Parse(TurretLevel((10, 16, 'I'), (11, 16, '=')));
Check("κάθετος και οριζόντιος δίπλα-δίπλα ΔΕΝ ενώνονται",
      axes.TurretGroups().Count == 2, axes.TurretGroups().Count.ToString());

var plain = LevelDocument.Parse(TurretLevel((10, 16, 'I')));
plain.SetTurretLinks([new TurretLink(10, 16, 0, TurretGraph.DefaultReload, 0)]);
Check("ολόκληρη προεπιλογή -> καμία γραμμή, καθαρό αρχείο",
      !plain.Footer.Any(TurretGraph.IsTurretLine),
      string.Join(" | ", plain.Footer));

var orphan = LevelDocument.Parse(TurretLevel((10, 16, 'I')));
orphan.SetTurretLinks([new TurretLink(3, 3, 4, 2, 3)]);
Check("δήλωση χωρίς πυργίσκο στο πλέγμα πετιέται",
      !orphan.Footer.Any(TurretGraph.IsTurretLine));

var stray = LevelDocument.Parse(TurretLevel((10, 16, 'I')));
stray.Footer.Add("turret 3 3 4 2 3");
Check("…και όταν έρχεται από το αρχείο, το λέει",
      stray.ValidateContent(_ => true).Warnings.Any(w => w.Contains("turret 3 3")),
      string.Join(" | ", stray.ValidateContent(_ => true).Warnings));

// Φόρτιση 0 ΧΩΡΙΣ ρυθμό σημαίνει «ρίχνει σε κάθε ενημέρωση»: στο μοντέλο το
// turret_ready βγαίνει ίσο με το ρολόι και ο πυργίσκος δεν σταματά ποτέ.
var clamped = TurretGraph.Clamp(new TurretLink(1, 1, 9, 0, 999));
Check("οι τιμές μπαίνουν στα όρια του παιχνιδιού",
      clamped is { Channel: 7, Reload: 1 } && clamped.Auto == TurretGraph.MaxSeconds,
      clamped.ToString());

var reload = LevelDocument.Parse(TurretLevel((10, 16, 'I')));
reload.SetTurretLinks([new TurretLink(10, 16, 0, 0, 0)]);
Check("…και γράφονται ήδη διορθωμένες",
      reload.Footer.Contains("turret 10 16 0 1 0"),
      string.Join(" | ", reload.Footer));

// Round-trip: αποθήκευση χωρίς αλλαγή δεν πολλαπλασιάζει γραμμές.
var twice = LevelDocument.Parse(TurretLevel((10, 16, 'I')));
twice.SetTurretLinks([new TurretLink(10, 16, 4, 2, 3)]);
var read = twice.TurretLinks().Single();
twice.SetTurretLinks([new TurretLink(10, 16, read.Channel, read.Reload, read.Auto)]);
Check("δεύτερη αποθήκευση δεν διπλασιάζει τη γραμμή",
      twice.Footer.Count(TurretGraph.IsTurretLine) == 1,
      string.Join(" | ", twice.Footer.Where(TurretGraph.IsTurretLine)));

// ============================================================ πλατφόρμες
//
// Η κινούμενη πλατφόρμα είναι το μόνο αντικείμενο που ΦΕΥΓΕΙ από το κελί του.
// Ό,τι ελέγχεται εδώ είναι τα σημεία όπου αυτό αλλάζει τους κανόνες.

Console.WriteLine("--- κινούμενες πλατφόρμες");

string PlatLevel(params (int Col, int Row, char Sym)[] cells)
{
    var rows = new List<string> { new('#', 40) };
    for (var i = 0; i < 22; i++) rows.Add("#" + new string('.', 38) + "#");
    rows.Add(new string('#', 40));
    foreach (var (c, r, sym) in cells)
    {
        var line = rows[r].ToCharArray();
        line[c] = sym;
        rows[r] = new string(line);
    }

    return "; platforms\n" + string.Join("\n", rows) + "\ngravity 0\n";
}

var pl = PlatformGraph.ParseLines(["plat 10 14 20 14 3 40"]).Single();
Check("η γραμμή διαβάζεται πλήρης",
      pl is { Col: 10, Row: 14, DestCol: 20, DestRow: 14, Channel: 3, Speed: 40 },
      pl.ToString());
Check("χωρίς ταχύτητα ισχύει η προεπιλογή",
      PlatformGraph.ParseLines(["plat 10 14 20 14 3"]).Single().Speed
          == PlatformGraph.DefaultSpeed);

// ΤΟ «plat» ΔΕΝ ΕΙΝΑΙ «plate». Τα δύο διαφέρουν σε ένα γράμμα και το ένα είναι
// πλάκα πίεσης: αν το ένα pattern έπιανε το άλλο, ο editor θα έσβηνε τη γραμμή
// της πλατφόρμας σε κάθε αποθήκευση.
Check("ο AttrGraph ΔΕΝ μπερδεύει το «plat» με το «plate»",
      !AttrGraph.IsAttrLine("plat 10 14 20 14 3 40")
      && !AttrGraph.IsAttrLine("plat 10 14 20"));
Check("…και ο PlatformGraph δεν πιάνει γραμμή πλάκας",
      !PlatformGraph.IsPlatformLine("plate 10 14 3"));

// Ίσια, κατακόρυφα και στις 45 μοίρες περνάνε· οτιδήποτε άλλο το απορρίπτει
// το μοντέλο με εξαίρεση, δηλαδή σπάει το χτίσιμο της δισκέτας.
foreach (var (dc, dr, ok, what) in new[]
         { (20, 14, true, "οριζόντια"), (10, 20, true, "κατακόρυφα"),
           (16, 20, true, "διαγώνια"), (17, 20, false, "λοξή") })
{
    Check($"διαδρομή {what}: {(ok ? "δεκτή" : "απορρίπτεται")}",
          PlatformGraph.PathOk(new PlatformLink(10, 14, dc, dr, 0, 24)) == ok);
}

var pdoc = LevelDocument.Parse(PlatLevel((10, 14, 'M'), (11, 14, 'M'), (12, 14, 'M')));
Check("γειτονικά κελιά είναι ΜΙΑ πλατφόρμα",
      pdoc.PlatformGroups().Single().Cells.Count == 3);
pdoc.SetPlatformLinks([new PlatformLink(10, 14, 20, 14, 3, 40)]);
Check("γράφεται ΜΙΑ γραμμή, στο πάνω-αριστερό κελί",
      pdoc.Footer.Count(PlatformGraph.IsPlatformLine) == 1
      && pdoc.Footer.Contains("plat 10 14 20 14 3 40"),
      string.Join(" | ", pdoc.Footer.Where(PlatformGraph.IsPlatformLine)));

// Δεύτερη αποθήκευση χωρίς αλλαγή δεν διπλασιάζει τη γραμμή.
var back = pdoc.PlatformLinks().Single();
pdoc.SetPlatformLinks([back]);
Check("δεύτερη αποθήκευση δεν διπλασιάζει",
      pdoc.Footer.Count(PlatformGraph.IsPlatformLine) == 1);

var pdef = LevelDocument.Parse(PlatLevel((10, 14, 'M')));
pdef.SetPlatformLinks([new PlatformLink(10, 14, 10, 14, 0, PlatformGraph.DefaultSpeed)]);
Check("αδήλωτη πλατφόρμα δεν αφήνει γραμμή", 
      !pdef.Footer.Any(PlatformGraph.IsPlatformLine),
      string.Join(" | ", pdef.Footer));
Check("…αλλά προειδοποιεί ότι δεν πάει πουθενά",
      pdef.ValidateContent(_ => true).Warnings.Any(w => w.Contains("no declared path")),
      string.Join(" | ", pdef.ValidateContent(_ => true).Warnings));

var pbad = LevelDocument.Parse(PlatLevel((10, 14, 'M')));
pbad.Footer.Add("plat 10 14 17 20 0 24");
var rep = pbad.ValidateContent(_ => true);
Check("λοξή διαδρομή είναι ΣΦΑΛΜΑ, όχι προειδοποίηση",
      rep.Errors.Any(e => e.Contains("45-degree")), string.Join(" | ", rep.Errors));

var poff = LevelDocument.Parse(PlatLevel((10, 14, 'm')));
Check("το «m» είναι κι αυτό πλατφόρμα, σταματημένη",
      poff.PlatformGroups().Count == 1);

var porph = LevelDocument.Parse(PlatLevel((10, 14, 'M')));
porph.SetPlatformLinks([new PlatformLink(3, 3, 9, 9, 1, 24)]);
Check("δήλωση χωρίς πλατφόρμα στο πλέγμα πετιέται",
      !porph.Footer.Any(PlatformGraph.IsPlatformLine));

var pclamp = LevelDocument.Parse(PlatLevel((10, 14, 'M')));
pclamp.SetPlatformLinks([new PlatformLink(10, 14, 20, 14, 9, 999)]);
Check("κανάλι και ταχύτητα μπαίνουν στα όρια",
      pclamp.Footer.Contains($"plat 10 14 20 14 7 {PlatformGraph.MaxSpeed}"),
      string.Join(" | ", pclamp.Footer));

// ΤΙ ΚΑΘΕΤΑΙ ΠΑΝΩ ΤΗΣ. Ο διακόπτης ΤΑΞΙΔΕΥΕΙ μαζί της· κάθε άλλο αντικείμενο
// θα έμενε καρφωμένο στο κελί του και θα κρεμόταν στον αέρα.
var pride = LevelDocument.Parse(PlatLevel((10, 14, 'M'), (11, 14, 'M'), (11, 13, 'S')));
pride.Footer.Add("plat 10 14 20 14 0 24");
Check("διακόπτης πάνω στην πλατφόρμα επιτρέπεται",
      !pride.ValidateContent(_ => true).Errors.Any(e => e.Contains("sits on top")),
      string.Join(" | ", pride.ValidateContent(_ => true).Errors));

foreach (var (sym, what) in new[] { ('k', "κλειδί"), ('B', "κιβώτιο"),
                                    ('^', "αγκάθι"), ('#', "στερεό") })
{
    var onTop = LevelDocument.Parse(PlatLevel((10, 14, 'M'), (11, 14, 'M'),
                                              (11, 13, sym)));
    onTop.Footer.Add("plat 10 14 20 14 0 24");
    Check($"{what} πάνω στην πλατφόρμα απορρίπτεται",
          onTop.ValidateContent(_ => true).Errors.Any(e => e.Contains("sits on top")),
          string.Join(" | ", onTop.ValidateContent(_ => true).Errors));
}

var two = LevelDocument.Parse(PlatLevel((10, 14, 'M'), (11, 14, 'M'),
                                        (10, 13, 'S'), (11, 13, 'S')));
two.Footer.Add("plat 10 14 20 14 0 24");
Check("δύο διακόπτες πάνω της απορρίπτονται",
      two.ValidateContent(_ => true).Errors.Any(e => e.Contains("carries 2")),
      string.Join(" | ", two.ValidateContent(_ => true).Errors));

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
