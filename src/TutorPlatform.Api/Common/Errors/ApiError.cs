namespace TutorPlatform.Api.Common.Errors;

public sealed record ApiError(string Error, string? Details = null);