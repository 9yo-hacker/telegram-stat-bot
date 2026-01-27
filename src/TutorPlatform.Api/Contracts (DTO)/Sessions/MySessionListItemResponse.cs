using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Sessions;

public record MySessionListItemResponse(
    Guid Id,
    DateTime StartsAt,
    int DurationMinutes,
    SessionStatus Status
);
