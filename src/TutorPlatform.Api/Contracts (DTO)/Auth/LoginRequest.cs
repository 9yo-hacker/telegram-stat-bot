using System.ComponentModel.DataAnnotations;

namespace TutorPlatform.Api.Contracts.Auth;

public sealed class LoginRequest
{
    [Required, EmailAddress, MaxLength(254)] public string Email { get; init; } = default!;

    [Required, MinLength(6), MaxLength(30)] public string Password { get; init; } = default!;
}
