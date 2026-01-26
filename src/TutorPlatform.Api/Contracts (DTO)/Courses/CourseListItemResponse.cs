using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Courses;

public record CourseListItemResponse(
    Guid Id,
    string Title,
    CourseStatus Status,
    DateTime CreatedAt,
    DateTime UpdatedAt
);
