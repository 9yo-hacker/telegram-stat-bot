using TutorPlatform.Api.Contracts.Enrollments;

namespace TutorPlatform.Api.Application.Abstractions;

public interface IEnrollmentService
{
    Task<List<EnrollmentResponse>?> GetByCourseAsync(Guid teacherId, Guid courseId, CancellationToken ct);

    // create by studentCode
    Task<(EnrollmentResponse? enrollment, string? error)> CreateAsync(
        Guid teacherId, Guid courseId, string studentCode, CancellationToken ct);

    Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid enrollmentId, UpdateEnrollmentRequest req, CancellationToken ct);

    Task<(bool ok, string? error)> RevokeAsync(Guid teacherId, Guid enrollmentId, CancellationToken ct);
}
