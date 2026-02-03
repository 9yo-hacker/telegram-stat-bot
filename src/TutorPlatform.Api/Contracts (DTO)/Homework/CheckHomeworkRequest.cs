using System.ComponentModel.DataAnnotations;

namespace TutorPlatform.Api.Contracts.Homework;

public sealed record CheckHomeworkRequest(
    [MaxLength(4000)] string? Comment,
    [Range(0, 100)] int? Grade
);
