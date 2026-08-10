using System.Diagnostics;
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
public sealed class BuildController(ILogger<BuildController> log) : ControllerBase
{
    // Η ρίζα του repo: ο editor τρέχει από τον υποφάκελο editor/.
    private static string RepoRoot =>
        Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), ".."));

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

        var (code, output) = await RunAsync(script);
        var dsk = Path.Combine(RepoRoot, "build", "gravassist.dsk");
        log.LogInformation("Build for room {Room}: exit code {Code}", req.Room, code);

        return Ok(new
        {
            ok = code == 0 && System.IO.File.Exists(dsk),
            room = req.Room,
            dsk = code == 0 && System.IO.File.Exists(dsk) ? "build/gravassist.dsk" : null,
            bytes = System.IO.File.Exists(dsk) ? new FileInfo(dsk).Length : 0,
            output = Tail(output, 40),
        });
    }

    private static async Task<(int, string)> RunAsync(string script)
    {
        var psi = new ProcessStartInfo("/bin/bash")
        {
            WorkingDirectory = RepoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
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
