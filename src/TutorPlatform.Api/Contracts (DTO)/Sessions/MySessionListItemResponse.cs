using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Sessions;

public record MySessionListItemResponse(
    Guid Id,
    Guid CourseId,
    Guid? LessonId,
    DateTime StartsAt,
    int DurationMinutes,
    SessionStatus Status,
    string? VideoLinkEffective
);
