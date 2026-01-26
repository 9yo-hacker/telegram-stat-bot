using TutorPlatform.Api.Contracts.Courses;

namespace TutorPlatform.Api.Application.Abstractions;

public interface ICourseService
{
    Task<List<CourseListItemResponse>> GetMyCoursesAsync(Guid teacherId, CancellationToken ct);
    Task<CourseResponse?> GetMyCourseAsync(Guid teacherId, Guid courseId, CancellationToken ct);
    Task<CourseResponse> CreateAsync(Guid teacherId, CreateCourseRequest req, CancellationToken ct);
    Task<bool> UpdateAsync(Guid teacherId, Guid courseId, UpdateCourseRequest req, CancellationToken ct);
    Task<bool> ArchiveAsync(Guid teacherId, Guid courseId, CancellationToken ct);
}
