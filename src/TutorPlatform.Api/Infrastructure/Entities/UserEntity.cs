namespace TutorPlatform.Api.Infrastructure;

public enum UserRole
{
    Teacher = 1,
    Student = 2
}

public class UserEntity
{
    public Guid Id { get; set; } = Guid.NewGuid();

    public string Email { get; set; } = null!;
    public string PasswordHash { get; set; } = null!;
    public UserRole Role { get; set; }
    public string Name { get; set; } = null!;

    public string? StudentCode { get; set; } // only for Student
    public bool IsActive { get; set; } = true;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }
}
