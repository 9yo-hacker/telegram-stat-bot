using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Courses;

public record UpdateCourseRequest(
    string? Title,
    string? Description,
    string? DefaultVideoLink,
    CourseStatus? Status
);