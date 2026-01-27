using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Errors;
using TutorPlatform.Api.Contracts.Auth;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Auth;

public sealed class AuthService
{
    private readonly AppDbContext _db;
    private readonly IPasswordHasher _passwordHasher;
    private readonly IJwtTokenService _jwt;
    private readonly IClock _clock;

    public AuthService(
        AppDbContext db,
        IPasswordHasher passwordHasher,
        IJwtTokenService jwt,
        IClock clock)
    {
        _db = db;
        _passwordHasher = passwordHasher;
        _jwt = jwt;
        _clock = clock;
    }

    public async Task<AuthResponse> Register(RegisterRequest req, CancellationToken ct)
    {
        var email = req.Email.Trim().ToLowerInvariant();
        var name  = req.Name.Trim();

        var exists = await _db.Users.AnyAsync(x => x.Email == email, ct);
        if (exists) throw new EmailAlreadyExistsException(email);

        var role = ParseRole(req.Role);

        var user = new UserEntity
        {
            Id = Guid.NewGuid(),
            Email = email,
            Name = name,
            Role = role,
            PasswordHash = _passwordHasher.Hash(req.Password),
            IsActive = true,
            CreatedAt = _clock.UtcNow.UtcDateTime,
            UpdatedAt = _clock.UtcNow.UtcDateTime,
            StudentCode = null
        };

        if (role == UserRole.Student)
            user.StudentCode = await GenerateUniqueStudentCode(ct);

        _db.Users.Add(user);
        await _db.SaveChangesAsync(ct);

        var token = _jwt.CreateAccessToken(user);

        return new AuthResponse
        {
            AccessToken = token,
            User = AuthMapper.MapProfile(user)
        };
    }

    public async Task<AuthResponse> Login(LoginRequest req, CancellationToken ct)
    {
        var email = req.Email.Trim().ToLowerInvariant();

        var user = await _db.Users.SingleOrDefaultAsync(x => x.Email == email, ct);
        if (user is null) throw new InvalidCredentialsException();

        var ok = _passwordHasher.Verify(req.Password, user.PasswordHash);
        if (!ok) throw new InvalidCredentialsException();

        var token = _jwt.CreateAccessToken(user);

        return new AuthResponse
        {
            AccessToken = token,
            User = AuthMapper.MapProfile(user)
        };
    }

    private static UserRole ParseRole(string role)
    {
        return role.Trim().ToLowerInvariant() switch
        {
            "teacher" => UserRole.Teacher,
            "student" => UserRole.Student,
            _ => throw new InvalidRoleException(role) // сделай такой exception -> 400
        };
    }

    private async Task<string> GenerateUniqueStudentCode(CancellationToken ct)
    {
        // MVP: простой retry. Гарантия всё равно на unique index.
        for (var attempt = 0; attempt < 20; attempt++)
        {
            var code = RandomDigits(9); 
            var exists = await _db.Users.AnyAsync(x => x.StudentCode == code, ct);
            if (!exists) return code;
        }

        // совсем редко, но пусть будет fallback
        return RandomDigits(10);
    }

    private static string RandomDigits(int len)
    {
        var rnd = Random.Shared;
        var chars = new char[len];
        for (var i = 0; i < len; i++)
            chars[i] = (char)('0' + rnd.Next(0, 10));
        return new string(chars);
    }
}
