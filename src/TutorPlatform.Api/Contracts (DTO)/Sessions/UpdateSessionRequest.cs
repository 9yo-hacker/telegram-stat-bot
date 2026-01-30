using System.ComponentModel.DataAnnotations;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Sessions;

public record UpdateSessionRequest(
    DateTime? StartsAt,
    [Range(1, 1440)]
    int? DurationMinutes,
    Guid? LessonId,
    string? VideoLink,
    // минимум не опредеялть, а максимум 2000 символов
    string? Notes,
    SessionStatus? Status // разрешим Planned/Canceled, Done — только через /complete
);
