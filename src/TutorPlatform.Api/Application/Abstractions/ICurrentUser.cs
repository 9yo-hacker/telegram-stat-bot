using System.Security.Claims;

namespace TutorPlatform.Api.Application.Abstractions;

public interface ICurrentUser
{
    bool IsAuthenticated { get; }
    Guid? UserId { get; }
    string? Email { get; }
    string? Role { get; }
    ClaimsPrincipal? Principal { get; }
}
