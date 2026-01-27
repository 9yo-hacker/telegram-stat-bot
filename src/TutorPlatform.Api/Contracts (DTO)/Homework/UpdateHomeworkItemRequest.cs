using System.ComponentModel.DataAnnotations;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Homework;

public record UpdateHomeworkItemRequest(
    [MaxLength(200)] string? Title,
    [MaxLength(4000)] string? Description,
    [MaxLength(2000)] string? LinkUrl,
    DateTime? DueAt,
    HomeworkStatus? Status
);
