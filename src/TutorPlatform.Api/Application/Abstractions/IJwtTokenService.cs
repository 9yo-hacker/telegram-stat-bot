using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Abstractions;

public interface IJwtTokenService
{
    string CreateAccessToken(UserEntity user);
}
