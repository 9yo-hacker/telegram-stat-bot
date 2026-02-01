namespace TutorPlatform.Api.Contracts.Auth;

public sealed record PasswordResetConfirmRequest(string Token, string NewPassword);
