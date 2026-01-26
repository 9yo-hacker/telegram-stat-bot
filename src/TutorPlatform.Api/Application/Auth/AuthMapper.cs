using TutorPlatform.Api.Contracts.Auth;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Auth;

public static class AuthMapper
{
    public static UserProfileDto MapProfile(UserEntity u) =>
        new(
            u.Id,
            u.Email,
            u.Name,
            u.Role.ToString(),
            u.StudentCode
        );
}

