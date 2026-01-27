using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Sessions;

public record SessionResponse(
    Guid Id,
    Guid CourseId,
    Guid TeacherId,
    Guid StudentId,
    Guid? LessonId,
    DateTime StartsAt,
    int DurationMinutes,
    SessionStatus Status,
    string? VideoLink,
    string? Notes,
    string? LessonTitleSnapshot,
    string? LessonMaterialUrlSnapshot,
    DateTime CreatedAt,
    DateTime UpdatedAt
);
