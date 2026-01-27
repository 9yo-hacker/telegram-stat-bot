using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Enrollments;

public record EnrollmentResponse(
    Guid Id,
    Guid CourseId,
    Guid StudentId,
    string? Plan,
    string? Progress,
    EnrollmentStatus Status,
    DateTime CreatedAt,
    DateTime UpdatedAt
);
