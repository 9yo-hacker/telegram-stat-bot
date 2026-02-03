namespace TutorPlatform.Api.Contracts.Homework;

public sealed record MyHomeworkDetailsResponse(
    Guid Id,
    Guid CourseId,
    Guid EnrollmentId,
    string Title,
    string? Description,
    string? LinkUrl,
    DateTime? DueAt,

    // task/answer
    string? StudentAnswer,
    DateTime? StudentAnswerSubmittedAt,

    // checked
    bool IsChecked,
    string? TeacherComment,
    int? TeacherGrade,
    DateTime? CheckedAt,

    DateTime CreatedAt,
    DateTime UpdatedAt
);
