namespace TutorPlatform.Api.Contracts.Lessons;

public sealed record CreateLessonRequest(
    string Title,
    string? MaterialUrl,
    LessonStatus Status
);
