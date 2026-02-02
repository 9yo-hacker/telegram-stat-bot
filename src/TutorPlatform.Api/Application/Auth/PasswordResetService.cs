using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;
using Microsoft.Extensions.Logging; 

namespace TutorPlatform.Api.Application.Auth;

public sealed class PasswordResetService : IPasswordResetService
{
    private readonly AppDbContext _db;
    private readonly IPasswordHasher _hash;
    private readonly IClock _clock;
    private readonly IConfiguration _cfg;
    private readonly IEmailSender _email;
    private readonly ILogger<PasswordResetService> _log;

    public PasswordResetService(
        AppDbContext db,
        IPasswordHasher hash,
        IClock clock,
        IConfiguration cfg,
        IEmailSender email,
        ILogger<PasswordResetService> log)
    {
        _db = db;
        _hash = hash;
        _clock = clock;
        _cfg = cfg;
        _email = email;
        _log = log;
    }

    public async Task<string?> RequestAsync(string email, CancellationToken ct)
    {
        var norm = email.Trim().ToLowerInvariant();

        var user = await _db.Users.SingleOrDefaultAsync(x => x.Email == norm, ct);

        // не раскрываем, существует ли email
        if (user is null) return null;

        var now = _clock.UtcNow.UtcDateTime;
        var ttl = GetTtlMinutes();
        var expires = now.AddMinutes(ttl);

        var token = GenerateToken();
        var tokenHash = Sha256Base64(token);

        var ent = new PasswordResetTokenEntity
        {
            Id = Guid.NewGuid(),
            UserId = user.Id,
            TokenHash = tokenHash,
            CreatedAt = now,
            ExpiresAt = expires,
            UsedAt = null
        };

        _db.PasswordResetTokens.Add(ent);
        await _db.SaveChangesAsync(ct);

        // отправка письма со ссылкой
        // если SMTP не настроен — лучше падать на dev, а на prod успеется настроить.
        var baseUrl = _cfg["Frontend:BaseUrl"] ?? "http://localhost:3000";
        var link = $"{baseUrl.TrimEnd('/')}/reset-password?token={Uri.EscapeDataString(token)}";

        var subject = "Восстановление пароля";
        var html = $@"
        <p>Кто-то запросил восстановление пароля для вашего аккаунта.</p>
        <p>Если это вы — задайте новый пароль по ссылке (действует {ttl} минут):</p>
        <p><a href=""{link}"">{link}</a></p>
        <p>Если это были не вы — просто игнорируйте письмо.</p>
        ";

        try
        {
            await _email.SendAsync(user.Email, subject, html, ct);
        }
        catch (Exception ex)
        {
            // endpoint всё равно должен отвечать 200 (анти-enumeration),
            _log.LogError(ex, "Password reset email send failed for {Email}", user.Email);
        }
        // токен возвращаем (контроллер всё равно отдаст его только в dev при X-Dev-Seed)
        return token;
    }

    public async Task<(bool ok, string? error)> ConfirmAsync(string token, string newPassword, CancellationToken ct)
    {
        var now = _clock.UtcNow.UtcDateTime;

        var hash = Sha256Base64(token);

        var pr = await _db.PasswordResetTokens
            .Include(x => x.User)
            .SingleOrDefaultAsync(x => x.TokenHash == hash, ct);

        if (pr is null) return (false, "invalid_or_expired");
        if (pr.UsedAt is not null) return (false, "invalid_or_expired");
        if (pr.ExpiresAt <= now) return (false, "invalid_or_expired");

        pr.User.PasswordHash = _hash.Hash(newPassword);
        pr.User.UpdatedAt = now;

        pr.UsedAt = now;

        var others = await _db.PasswordResetTokens
            .Where(x => x.UserId == pr.UserId && x.UsedAt == null && x.Id != pr.Id)
            .ToListAsync(ct);

        foreach (var t in others)
            t.UsedAt = now;

        await _db.SaveChangesAsync(ct);

        return (true, null);
    }

    private int GetTtlMinutes()
        => int.TryParse(_cfg["PasswordReset:TtlMinutes"], out var m) ? m : 20;

    private static string GenerateToken()
    {
        var bytes = RandomNumberGenerator.GetBytes(32);
        return Base64UrlEncoder.Encode(bytes);
    }

    private static string Sha256Base64(string s)
    {
        var bytes = Encoding.UTF8.GetBytes(s);
        var hash = SHA256.HashData(bytes);
        return Convert.ToBase64String(hash);
    }
}
