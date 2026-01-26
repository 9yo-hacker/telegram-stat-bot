using System.Security.Claims;

namespace TutorPlatform.Api.Common.Auth;

public static class ClaimsPrincipalExtensions
{
    public static Guid GetUserId(this ClaimsPrincipal user)
    {
        var id = user.FindFirstValue(ClaimTypes.NameIdentifier);
        if (string.IsNullOrWhiteSpace(id) || !Guid.TryParse(id, out var guid))
            throw new InvalidOperationException("UserId claim is missing or invalid.");

        return guid;
    }
}
