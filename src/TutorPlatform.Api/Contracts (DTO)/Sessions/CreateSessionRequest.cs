using System.ComponentModel.DataAnnotations;

namespace TutorPlatform.Api.Contracts.Sessions;

public record CreateSessionRequest(
    Guid CourseId,
    Guid StudentId,
    DateTime StartsAt,
    [Range(1, 1440)]
    int DurationMinutes,
    Guid? LessonId,
    //если поле обязательное то 4, а максимум 2048 символов
    string? VideoLink,
    string? Notes
);
