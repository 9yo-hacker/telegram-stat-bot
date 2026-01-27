namespace TutorPlatform.Api.Contracts.Lessons;

public sealed record UpdateLessonRequest(
    string? Title,
    string? MaterialUrl,
    LessonStatus? Status
);
