namespace TutorPlatform.Api.Contracts.Auth;

public sealed record UserProfileDto(
    Guid Id, 
    string Email, 
    string Name, 
    string Role, 
    string? StudentCode
    );
