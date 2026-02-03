namespace TutorPlatform.Api.Contracts.Lessons;

/// <summary>
/// Student view of lesson in a course.
/// Filter on UI is based on sessions (planned/done) for this student.
/// </summary>
public sealed record MyLessonListItemResponse(
    Guid Id,
    Guid CourseId,
    string Title,
    string? MaterialUrl,
    LessonStatus Status,

    bool HasPlannedSessions,
    bool HasDoneSessions,
    DateTime? NextPlannedSessionAt,
    DateTime? LastDoneSessionAt
);
