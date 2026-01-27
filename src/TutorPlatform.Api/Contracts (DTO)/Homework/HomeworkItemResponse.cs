using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Homework;

public record HomeworkItemResponse(
    Guid Id,
    Guid EnrollmentId,
    Guid CreatedByTeacherId,
    string Title,
    string? Description,
    string? LinkUrl,
    DateTime? DueAt,
    HomeworkStatus Status,
    DateTime? CompletedAt,
    DateTime CreatedAt,
    DateTime UpdatedAt
);
