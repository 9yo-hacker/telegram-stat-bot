namespace TutorPlatform.Api.Application.Abstractions;

public interface IPasswordResetService
{
    // Возвращаем токен только для dev-режима - теста фронта
    Task<string?> RequestAsync(string email, CancellationToken ct);

    Task<(bool ok, string? error)> ConfirmAsync(string token, string newPassword, CancellationToken ct);
}
