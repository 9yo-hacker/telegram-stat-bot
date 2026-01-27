namespace TutorPlatform.Api.Data.Entities;

public sealed class LessonEntity
{
    public Guid Id { get; set; }
    public Guid CourseId { get; set; }
    public string Title { get; set; } = null!;
    public string? MaterialUrl { get; set; }
    public LessonStatus Status { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
    public CourseEntity Course { get; set; } = null!;
}
