namespace TutorPlatform.Api.Data.Entities;

public class HomeworkItemEntity
{
    public Guid Id { get; set; }

    public Guid EnrollmentId { get; set; }
    public Guid CreatedByTeacherId { get; set; }

    public string Title { get; set; } = null!;
    public string? Description { get; set; }
    public string? LinkUrl { get; set; }
    public DateTime? DueAt { get; set; } // UTC

    public HomeworkStatus Status { get; set; } = HomeworkStatus.Todo;

    // Todo -> null, Done/Skipped -> now
    public DateTime? CompletedAt { get; set; }

    // Student answer (Phase 2 but DTOs already planned)
    public string? StudentAnswer { get; set; }
    public DateTime? StudentAnswerSubmittedAt { get; set; }

    // Teacher review ("checked")
    public string? TeacherComment { get; set; }
    public int? TeacherGrade { get; set; } // 0..100 (decide in UI)
    public DateTime? CheckedAt { get; set; }

    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public EnrollmentEntity Enrollment { get; set; } = null!;
    public UserEntity CreatedByTeacher { get; set; } = null!;
}
