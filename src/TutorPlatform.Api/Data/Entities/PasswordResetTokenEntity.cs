namespace TutorPlatform.Api.Data.Entities;

public sealed class PasswordResetTokenEntity
{
    public Guid Id { get; set; }

    public Guid UserId { get; set; }
    public UserEntity User { get; set; } = null!;

    public string TokenHash { get; set; } = null!;
    public DateTime ExpiresAt { get; set; }
    public DateTime? UsedAt { get; set; }
    public DateTime CreatedAt { get; set; }
}
