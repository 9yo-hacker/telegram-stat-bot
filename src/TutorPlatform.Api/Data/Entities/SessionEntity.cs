namespace TutorPlatform.Api.Data.Entities;

public class SessionEntity
{
    public Guid Id { get; set; }

    public Guid CourseId { get; set; }
    public Guid TeacherId { get; set; }
    public Guid StudentId { get; set; }
    public Guid? LessonId { get; set; }

    public DateTime StartsAt { get; set; } // UTC
    public int DurationMinutes { get; set; }

    public string? VideoLink { get; set; }
    public string? Notes { get; set; }

    public SessionStatus Status { get; set; } = SessionStatus.Planned;

    // Snapshot (фиксируем при Done)
    public string? LessonTitleSnapshot { get; set; }
    public string? LessonMaterialUrlSnapshot { get; set; }

    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public CourseEntity Course { get; set; } = null!;
    public UserEntity Teacher { get; set; } = null!;
    public UserEntity Student { get; set; } = null!;
    public LessonEntity? Lesson { get; set; }
}
