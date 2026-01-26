using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Infrastructure.Security;

public sealed class JwtTokenService : IJwtTokenService
{
    private readonly IConfiguration _cfg;

    public JwtTokenService(IConfiguration cfg) => _cfg = cfg;

    public string CreateAccessToken(UserEntity user)
{
    var issuer = _cfg["Jwt:Issuer"] ?? throw new InvalidOperationException("Jwt:Issuer missing");
    var audience = _cfg["Jwt:Audience"] ?? throw new InvalidOperationException("Jwt:Audience missing");
    var key = _cfg["Jwt:Key"] ?? throw new InvalidOperationException("Jwt:Key missing");
    var minutes = int.TryParse(_cfg["Jwt:AccessTokenMinutes"], out var m) ? m : 120;

    var keyBytes = Encoding.UTF8.GetBytes(key);
    if (keyBytes.Length < 32)
        throw new InvalidOperationException("Jwt:Key must be at least 32 bytes for HS256.");

    var signingKey = new SymmetricSecurityKey(keyBytes);
    var creds = new SigningCredentials(signingKey, SecurityAlgorithms.HmacSha256);

    var claims = new List<Claim>
    {
        new(JwtRegisteredClaimNames.Sub, user.Id.ToString()),
        new(ClaimTypes.NameIdentifier, user.Id.ToString()),
        new(JwtRegisteredClaimNames.Email, user.Email),
        new(ClaimTypes.Role, user.Role.ToString()),
        new(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
        new(JwtRegisteredClaimNames.Iat, DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(), ClaimValueTypes.Integer64),
    };

    var token = new JwtSecurityToken(
        issuer: issuer,
        audience: audience,
        claims: claims,
        expires: DateTime.UtcNow.AddMinutes(minutes),
        signingCredentials: creds
    );

    return new JwtSecurityTokenHandler().WriteToken(token);
}

}