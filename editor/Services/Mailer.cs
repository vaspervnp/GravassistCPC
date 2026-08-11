using System.Net;
using System.Net.Mail;

namespace GravassistEditor.Services;

/// <summary>
/// Αποστολή email μέσω SMTP.
///
/// ΜΕ ΤΟΝ ΕΝΣΩΜΑΤΩΜΕΝΟ SmtpClient, χωρίς πακέτο: ο editor δεν έχει καμία
/// εξάρτηση από CDN ή υπηρεσία, και δεν υπάρχει λόγος να αποκτήσει μία για να
/// στείλει δύο ειδών μήνυμα. ΠΡΟΣΟΧΗ: ο SmtpClient κάνει STARTTLS (θύρα 587)
/// αλλά ΔΕΝ υποστηρίζει implicit TLS (θύρα 465).
///
/// ΑΝ ΔΕΝ ΕΙΝΑΙ ΡΥΘΜΙΣΜΕΝΟ, ο editor δουλεύει κανονικά — απλώς δεν προσφέρει
/// σύνδεση με email. Αυτό διαφέρει σκόπιμα από τη σύνδεση Google, που αν
/// λείπει σταματά το ξεκίνημα: εκεί η απουσία σημαίνει «ανοιχτός editor», εδώ
/// σημαίνει «ένας τρόπος σύνδεσης λιγότερος».
/// </summary>
public sealed class Mailer(IConfiguration config, ILogger<Mailer> log)
{
    public const string HostVar = "gravassistSmtpHost";
    public const string PortVar = "gravassistSmtpPort";
    public const string UserVar = "gravassistSmtpUser";
    public const string PassVar = "gravassistSmtpPass";
    public const string FromVar = "gravassistMailFrom";
    public const string NameVar = "gravassistMailName";
    public const string TlsVar = "gravassistSmtpTls";
    public const string BaseUrlVar = "gravassistBaseUrl";

    private string? Host => Blank(config[HostVar]);
    private string? User => Blank(config[UserVar]);
    private string? Pass => Blank(config[PassVar]);

    /// <summary>Ο αποστολέας· αν λείπει, ο ίδιος ο λογαριασμός SMTP.</summary>
    public string? From => Blank(config[FromVar]) ?? User;

    public string DisplayName => Blank(config[NameVar]) ?? "GRAVASSIST editor";

    public int Port =>
        int.TryParse(config[PortVar], out var p) && p is > 0 and < 65536 ? p : 587;

    /// <summary>
    /// STARTTLS; ΕΝΕΡΓΟ εκτός αν το κλείσεις ρητά με «false».
    /// Υπάρχει μόνο για relay στο ίδιο μηχάνημα, που συχνά δεν σηκώνει TLS.
    /// Πάνω από δίκτυο, κλείνοντάς το στέλνεις τους κωδικούς σύνδεσης
    /// καθαρό κείμενο.
    /// </summary>
    public bool UseTls =>
        !string.Equals(config[TlsVar], "false", StringComparison.OrdinalIgnoreCase);

    /// <summary>Μπορεί να σταλεί email; Αλλιώς ο editor κρύβει τη σύνδεση με email.</summary>
    public bool IsConfigured => Host is not null && From is not null;

    /// <summary>
    /// Η δημόσια διεύθυνση για τους συνδέσμους μέσα στα email.
    /// Από τη ρύθμιση αν υπάρχει, αλλιώς από το ίδιο το αίτημα — που είναι
    /// σωστό μόνο επειδή ο editor διορθώνει scheme/host με forwarded headers.
    /// </summary>
    public string BaseUrl(HttpRequest request)
    {
        var configured = Blank(config[BaseUrlVar]);
        return (configured ?? $"{request.Scheme}://{request.Host}").TrimEnd('/');
    }

    /// <summary>
    /// Στέλνει ένα μήνυμα κειμένου. Επιστρέφει αν τα κατάφερε.
    /// ΔΕΝ πετάει: ο καλών πρέπει να απαντήσει στον χρήστη, όχι να σκάσει.
    /// </summary>
    public async Task<bool> SendAsync(string to, string subject, string body)
    {
        if (!IsConfigured)
        {
            log.LogWarning("Δεν στάλθηκε email προς {To}: λείπει η ρύθμιση SMTP "
                           + "({Host}, {From}).", to, HostVar, FromVar);
            return false;
        }

        try
        {
            using var client = new SmtpClient(Host!, Port)
            {
                EnableSsl = UseTls,             // STARTTLS
                DeliveryMethod = SmtpDeliveryMethod.Network,
                Timeout = 20_000,
            };
            // Χωρίς διαπιστευτήρια ο SmtpClient θα έστελνε ανώνυμα· κάποιοι
            // εσωτερικοί relay το δέχονται, οπότε δεν το επιβάλλουμε.
            if (User is not null && Pass is not null)
                client.Credentials = new NetworkCredential(User, Pass);

            using var msg = new MailMessage
            {
                From = new MailAddress(From!, DisplayName),
                Subject = subject,
                Body = body,
                IsBodyHtml = false,
            };
            msg.To.Add(to);

            await client.SendMailAsync(msg);
            log.LogInformation("Email προς {To}: {Subject}", to, subject);
            return true;
        }
        catch (Exception ex) when (ex is SmtpException or InvalidOperationException
                                      or FormatException or IOException)
        {
            // ΟΛΟΚΛΗΡΟ το σφάλμα στο log: μια αποτυχία SMTP είναι σχεδόν πάντα
            // ρύθμιση (λάθος θύρα, app password, αποστολέας που δεν ταιριάζει)
            // και το μήνυμα του παρόχου λέει ακριβώς ποιο.
            log.LogError(ex, "Απέτυχε η αποστολή email προς {To} μέσω {Host}:{Port}.",
                         to, Host, Port);
            return false;
        }
    }

    private static string? Blank(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
