namespace TutorPlatform.Api.Contracts.Homework;

public sealed record MyHomeworkListItemResponse(
    Guid Id,
    Guid CourseId,
    Guid EnrollmentId,
    string Title,
    DateTime? DueAt,
    bool IsChecked,
    DateTime CreatedAt,
    DateTime UpdatedAt
);
