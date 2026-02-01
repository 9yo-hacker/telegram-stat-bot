using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Auth;

public sealed class PasswordResetService : IPasswordResetService
{
    private readonly AppDbContext _db;
    private readonly IPasswordHasher _hash;
    private readonly IClock _clock;
    private readonly IConfiguration _cfg;

    public PasswordResetService(AppDbContext db, IPasswordHasher hash, IClock clock, IConfiguration cfg)
    {
        _db = db;
        _hash = hash;
        _clock = clock;
        _cfg = cfg;
    }

    public async Task<string?> RequestAsync(string email, CancellationToken ct)
    {
        var norm = email.Trim().ToLowerInvariant();

        var user = await _db.Users.SingleOrDefaultAsync(x => x.Email == norm, ct);

        // не раскрываем, существует ли email.
        if (user is null) return null;

        // 20 минут для MVP
        var now = _clock.UtcNow.UtcDateTime;
        var expires = now.AddMinutes(GetTtlMinutes());

        // генерируем url-safe token
        var token = GenerateToken();
        var tokenHash = Sha256Base64(token);

        // редко, но на всякий — если вдруг уникальный индекс поймает коллизию, можно ретраить
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

        // здесь позже будет отправка email (ссылки). Пока фронт может брать token в dev.
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

        // ставим новый пароль
        pr.User.PasswordHash = _hash.Hash(newPassword);
        pr.User.UpdatedAt = now;

        // токен одноразовый
        pr.UsedAt = now;

        // инвалидируем все другие активные токены этого пользователя
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
        return Base64UrlEncoder.Encode(bytes); // url-safe
    }

    private static string Sha256Base64(string s)
    {
        var bytes = Encoding.UTF8.GetBytes(s);
        var hash = SHA256.HashData(bytes);
        return Convert.ToBase64String(hash);
    }
}
