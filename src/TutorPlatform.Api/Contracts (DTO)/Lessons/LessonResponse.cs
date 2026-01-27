namespace TutorPlatform.Api.Contracts.Lessons;

public sealed record LessonResponse(
    Guid Id,
    Guid CourseId,
    string Title,
    string? MaterialUrl,
    LessonStatus Status
);
