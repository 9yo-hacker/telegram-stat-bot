using System.ComponentModel.DataAnnotations;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Homework;

public record CreateHomeworkItemRequest(
    // минимум определить как 4 символа а максимум 2000
    [Required, MaxLength(200)] string Title,
    // минимум не определять, а если поле обязательное то 4, максимум 2000
    [MaxLength(4000)] string? Description,
    // минимум не определять, а если поле обязательное то 4, максимум 2048
    [MaxLength(2000)] string? LinkUrl,
    // удосоверься что дату сдачи нельзя установить в прошлом или если это можно сделать то ок
    DateTime? DueAt,
    HomeworkStatus? Status
);
