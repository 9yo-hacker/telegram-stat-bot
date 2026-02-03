using System.ComponentModel.DataAnnotations;

namespace TutorPlatform.Api.Contracts.Homework;

public sealed record SubmitHomeworkAnswerRequest(
    [Required, MaxLength(4000)] string Answer
);
