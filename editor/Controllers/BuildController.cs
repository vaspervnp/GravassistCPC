using System.Diagnostics;
using GravassistEditor.Services;
using Microsoft.AspNetCore.Mvc;

namespace GravassistEditor.Controllers;

/// <summary>
/// Χτίσιμο του .dsk για τον Amstrad, με επιλεγμένη αίθουσα εκκίνησης.
///
/// Το test run στον browser και το .dsk εξυπηρετούν διαφορετικά πράγματα: το
/// πρώτο δοκιμάζει γρήγορα τον σχεδιασμό, το δεύτερο είναι το πραγματικό
/// παιχνίδι. Και τα δύο τρέφονται από τα ίδια αρχεία πίστας.
/// </summary>
[ApiController]
[Route("api/build")]
public sealed class BuildController(
    ILogger<BuildController> log, LevelStore store) : ControllerBase
{
    // Η ρίζα του repo: ο editor τρέχει από τον υποφάκελο editor/.
    private static string RepoRoot =>
        Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), ".."));

    /// <summary>
    /// ΕΝΑ χτίσιμο τη φορά. Το make δουλεύει σε ΚΟΙΝΟ build/ μέσα στο repo:
    /// δύο ταυτόχρονα χτισίματα θα πατούσαν το ένα τα ενδιάμεσα αρχεία του
    /// άλλου και θα κατέβαινε δισκέτα-χίμαιρα, χωρίς κανένα μήνυμα λάθους.
    /// </summary>
    private static readonly SemaphoreSlim BuildLock = new(1, 1);

    /// <summary>Το αντίγραφο του χρήστη — αυτό που κατεβαίνει.</summary>
    private string MyDsk => Path.Combine(store.RootPath, "gravassist.dsk");

    [HttpPost]
    public async Task<IActionResult> Build([FromBody] BuildRequest req)
    {
        // Ο αριθμός αίθουσας μπαίνει σε γραμμή εντολών — δεχόμαστε ΜΟΝΟ ακέραιο
        // σε λογικό εύρος, ώστε να μη μπορεί να γίνει έγχυση εντολής.
        if (req.Room is < 0 or > 9999)
            return BadRequest(new { error = "Invalid room number." });

        var script = req.Room > 0
            ? $"python3 tools/genasm.py --start {req.Room} && make"
            : "python3 tools/genasm.py && make";

        // Το χτίσιμο γίνεται πάνω στις ΔΙΚΕΣ ΤΟΥ αίθουσες: χωρίς αυτό, ο
        // καθένας θα έχτιζε τη δισκέτα κάποιου άλλου χωρίς να το καταλάβει.
        int code;
        string output;
        var dsk = Path.Combine(RepoRoot, "build", "gravassist.dsk");
        var ok = false;

        await BuildLock.WaitAsync();
        try
        {
            (code, output) = await RunAsync(script, store.RootPath);
            ok = code == 0 && System.IO.File.Exists(dsk);
            // Το αντίγραφο παίρνεται ΜΕΣΑ στο κλείδωμα: το κοινό build/
            // ανήκει στον επόμενο μόλις το αφήσουμε.
            if (ok) System.IO.File.Copy(dsk, MyDsk, overwrite: true);
        }
        finally
        {
            BuildLock.Release();
        }

        log.LogInformation("Build for room {Room}: exit code {Code}", req.Room, code);

        return Ok(new
        {
            ok,
            room = req.Room,
            dsk = ok ? "build/gravassist.dsk" : null,
            download = ok ? $"/api/build/dsk?room={req.Room}" : null,
            bytes = ok ? new FileInfo(MyDsk).Length : 0,
            output = Tail(output, 40),
        });
    }

    /// <summary>
    /// Κατεβάζει τη δισκέτα ΤΟΥ ΧΡΗΣΤΗ — το αντίγραφο που κρατήθηκε στο τέλος
    /// του δικού του χτισίματος, όχι το κοινό build/gravassist.dsk που μπορεί
    /// στο μεταξύ να το έχει ξαναγράψει κάποιος άλλος.
    /// </summary>
    [HttpGet("dsk")]
    public IActionResult Download(int room = 0)
    {
        if (!System.IO.File.Exists(MyDsk))
            return NotFound("Build the .dsk first.");

        var name = room is > 0 and <= 9999
            ? $"gravassist_room{room}.dsk"
            : "gravassist.dsk";
        // Διαβάζεται στη μνήμη: η δισκέτα είναι 178 KB και ένα ανοιχτό stream
        // θα κλείδωνε το αρχείο απέναντι στο επόμενο χτίσιμο.
        return File(System.IO.File.ReadAllBytes(MyDsk),
                    "application/octet-stream", name);
    }

    private static async Task<(int, string)> RunAsync(string script, string levels)
    {
        var psi = new ProcessStartInfo("/bin/bash")
        {
            WorkingDirectory = RepoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        // Περνιέται ως ΜΕΤΑΒΛΗΤΗ ΠΕΡΙΒΑΛΛΟΝΤΟΣ και όχι μέσα στην εντολή: η
        // διαδρομή περιέχει το email του χρήστη και δεν έχει καμία δουλειά να
        // περνά από φλοιό.
        psi.Environment["GRAVASSIST_LEVELS"] = levels;
        psi.ArgumentList.Add("-lc");
        psi.ArgumentList.Add(script);

        using var p = Process.Start(psi)!;
        var stdout = p.StandardOutput.ReadToEndAsync();
        var stderr = p.StandardError.ReadToEndAsync();
        await p.WaitForExitAsync();
        return (p.ExitCode, (await stdout) + (await stderr));
    }

    /// <summary>Μόνο οι τελευταίες γραμμές: το σφάλμα του assembler είναι εκεί.</summary>
    private static string Tail(string s, int lines)
    {
        var all = s.Replace("\r", "").Split('\n', StringSplitOptions.RemoveEmptyEntries);
        return string.Join("\n", all.Skip(Math.Max(0, all.Length - lines)));
    }
}

public sealed record BuildRequest(int Room);
