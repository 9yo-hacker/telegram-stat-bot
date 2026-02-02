using System.Net.Http.Json;
using Microsoft.Extensions.Options;
using TutorPlatform.Api.Application.Abstractions;

namespace TutorPlatform.Api.Application.Email;

public sealed class UnisenderGoEmailSender : IEmailSender
{
    private readonly HttpClient _http;
    private readonly UnisenderGoOptions _opt;
    private readonly ILogger<UnisenderGoEmailSender> _log;

    public UnisenderGoEmailSender(
        HttpClient http,
        IOptions<UnisenderGoOptions> opt,
        ILogger<UnisenderGoEmailSender> log)
    {
        _http = http;
        _opt = opt.Value;
        _log = log;
    }

    public async Task SendAsync(string toEmail, string subject, string htmlBody, CancellationToken ct)
    {
        // Unisender Go API: POST /ru/transactional/api/v1/email/send.json + X-API-KEY
        // Формат message/body/subject/from_email и т.п. — как в документации. :contentReference[oaicite:1]{index=1}

        if (string.IsNullOrWhiteSpace(_opt.ApiKey))
            throw new InvalidOperationException("UnisenderGo:ApiKey is missing");

        if (string.IsNullOrWhiteSpace(_opt.FromEmail))
            throw new InvalidOperationException("UnisenderGo:FromEmail is missing");

        var req = new
        {
            message = new
            {
                recipients = new[] { new { email = toEmail } },
                subject = subject,
                from_email = _opt.FromEmail,
                from_name = _opt.FromName,
                body = new
                {
                    html = htmlBody,
                    plaintext = StripHtmlFallback(htmlBody)
                },
                // можно включить трекинги позже
                track_links = 0,
                track_read = 0
            }
        };

        using var msg = new HttpRequestMessage(HttpMethod.Post, "email/send.json")
        {
            Content = JsonContent.Create(req)
        };
        msg.Headers.Add("X-API-KEY", _opt.ApiKey);

        var resp = await _http.SendAsync(msg, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            _log.LogError("UnisenderGo send failed: {Status} {Body}", (int)resp.StatusCode, body);
            throw new InvalidOperationException($"UnisenderGo send failed: {(int)resp.StatusCode}");
        }
    }

    private static string StripHtmlFallback(string html)
    {
        // примитивный fallback, чтобы plaintext не был пустым
        return html
            .Replace("<br>", "\n").Replace("<br/>", "\n").Replace("<br />", "\n")
            .Replace("</p>", "\n\n")
            .Replace("&nbsp;", " ")
            .Replace("&amp;", "&")
            .Replace("&lt;", "<")
            .Replace("&gt;", ">");
    }
}

public sealed class UnisenderGoOptions
{
    public string BaseUrl { get; set; } = "https://go1.unisender.ru/ru/transactional/api/v1/";
    public string ApiKey { get; set; } = "";
    public string FromEmail { get; set; } = "";
    public string FromName { get; set; } = "TutorPlatform";
}
