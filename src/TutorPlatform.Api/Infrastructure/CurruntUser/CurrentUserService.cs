using System.Security.Claims;
using TutorPlatform.Api.Application.Abstractions;

namespace TutorPlatform.Api.Infrastructure.CurrentUser;

public sealed class CurrentUserService : ICurrentUser
{
    private readonly IHttpContextAccessor _http;

    public CurrentUserService(IHttpContextAccessor http) => _http = http;
    public ClaimsPrincipal? Principal => _http.HttpContext?.User;
    public bool IsAuthenticated => Principal?.Identity?.IsAuthenticated == true;

    public Guid? UserId
    {
        get
        {
            var sub = Principal?.FindFirstValue(ClaimTypes.NameIdentifier)
                      ?? Principal?.FindFirstValue("sub")
                      ?? Principal?.FindFirstValue(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Sub);

            return Guid.TryParse(sub, out var id) ? id : null;
        }
    }

    public string? Email
        => Principal?.FindFirstValue(ClaimTypes.Email)
           ?? Principal?.FindFirstValue(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Email);

    public string? Role => Principal?.FindFirstValue(ClaimTypes.Role);
}
