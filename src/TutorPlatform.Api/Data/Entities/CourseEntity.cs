namespace TutorPlatform.Api.Data.Entities;

public sealed class CourseEntity
{
    public Guid Id { get; set; }
    public Guid TeacherId { get; set; }
    public UserEntity Teacher { get; set; } = null!;
    public string Title { get; set; } = null!;
    public string Description { get; set; } = null!;
    public string? DefaultVideoLink { get; set; }
    public CourseStatus Status { get; set; } = CourseStatus.Draft;
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public ICollection<LessonEntity> Lessons { get; set; } = new List<LessonEntity>();
    public ICollection<EnrollmentEntity> Enrollments { get; set; } = new List<EnrollmentEntity>();
    public ICollection<SessionEntity> Sessions { get; set; } = new List<SessionEntity>();
}
