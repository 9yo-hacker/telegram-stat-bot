using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Application.Abstractions;

public interface IHomeworkService
{
    Task<List<HomeworkItemResponse>?> GetByEnrollmentAsync(Guid teacherId, Guid enrollmentId, CancellationToken ct);
    Task<(HomeworkItemResponse? item, string? error)> CreateAsync(Guid teacherId, Guid enrollmentId, CreateHomeworkItemRequest req, CancellationToken ct);
    Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid homeworkId, UpdateHomeworkItemRequest req, CancellationToken ct);
    Task<(bool ok, string? error)> DeleteAsync(Guid teacherId, Guid homeworkId, CancellationToken ct);
}
