using System.ComponentModel.DataAnnotations;

namespace TutorPlatform.Api.Contracts.Auth;

public sealed class RegisterRequest
{
    [Required, EmailAddress, MaxLength(320)] public string Email { get; init; } = default!;

    [Required, MinLength(8), MaxLength(30)] public string Password { get; init; } = default!;

    [Required, MinLength(2), MaxLength(30)] public string Name { get; init; } = default!;

    [Required] public string Role { get; init; } = default!; // "Teacher" | "Student"
}