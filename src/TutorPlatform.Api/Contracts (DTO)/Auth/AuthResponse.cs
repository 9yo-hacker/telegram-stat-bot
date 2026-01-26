namespace TutorPlatform.Api.Contracts.Auth;

public sealed class AuthResponse
{
    public string AccessToken { get; init; } = default!;
    public UserProfileDto User { get; init; } = default!;
}
