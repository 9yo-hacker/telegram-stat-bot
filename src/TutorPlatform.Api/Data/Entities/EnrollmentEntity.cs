namespace TutorPlatform.Api.Data.Entities;

public class EnrollmentEntity
{
    public Guid Id { get; set; }
    public Guid CourseId { get; set; }
    public Guid StudentId { get; set; }
    public string? Plan { get; set; }
    public string? Progress { get; set; }
    public EnrollmentStatus Status { get; set; } = EnrollmentStatus.Active;
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public CourseEntity Course { get; set; } = null!;
    public UserEntity Student { get; set; } = null!;

    public ICollection<HomeworkItemEntity> HomeworkItems { get; set; } = new List<HomeworkItemEntity>();

}
