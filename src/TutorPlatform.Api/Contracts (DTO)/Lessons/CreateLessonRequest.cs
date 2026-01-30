namespace TutorPlatform.Api.Contracts.Lessons;

public sealed record CreateLessonRequest(
    // минимум 4 символа, а максимум 2000
    string Title,
    // минимум не определять, а если поле обязательное то 4, а максимум 2048 символов
    string? MaterialUrl,
    LessonStatus Status
);
