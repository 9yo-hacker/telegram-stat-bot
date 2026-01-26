using System.Security.Claims;

namespace TutorPlatform.Api.Common.Extensions;

public static class ClaimsPrincipalExtensions
{
    public static Guid GetUserId(this ClaimsPrincipal user)
    {
        // Мы кладём userId в JWT как sub
        var sub = user.FindFirstValue(ClaimTypes.NameIdentifier)
                  ?? user.FindFirstValue("sub");

        if (string.IsNullOrWhiteSpace(sub) || !Guid.TryParse(sub, out var id))
            throw new InvalidOperationException("User id claim is missing or invalid.");

        return id;
    }
}
