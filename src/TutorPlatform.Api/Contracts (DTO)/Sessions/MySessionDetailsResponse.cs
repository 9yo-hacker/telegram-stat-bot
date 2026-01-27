using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Sessions;

public record MySessionDetailsResponse(
    Guid Id,
    DateTime StartsAt,
    int DurationMinutes,
    SessionStatus Status,
    string? VideoLinkEffective,

    // Planned: live lesson material (если прикреплён LessonId)
    string? LiveLessonMaterialUrl,

    // Done: snapshot
    string? LessonTitleSnapshot,
    string? LessonMaterialUrlSnapshot
);
