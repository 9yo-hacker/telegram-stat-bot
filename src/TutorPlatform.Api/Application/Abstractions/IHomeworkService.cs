using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Application.Abstractions;

public interface IHomeworkService
{
    Task<List<HomeworkItemResponse>?> GetByEnrollmentAsync(Guid teacherId, Guid enrollmentId, CancellationToken ct);
    Task<(HomeworkItemResponse? item, string? error)> CreateAsync(Guid teacherId, Guid enrollmentId, CreateHomeworkItemRequest req, CancellationToken ct);
    Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid homeworkId, UpdateHomeworkItemRequest req, CancellationToken ct);
    Task<(bool ok, string? error)> DeleteAsync(Guid teacherId, Guid homeworkId, CancellationToken ct);

    // Student side
    Task<List<MyHomeworkListItemResponse>> GetMyAsync(Guid studentId, string? filter, CancellationToken ct);
    Task<MyHomeworkDetailsResponse?> GetMyByIdAsync(Guid studentId, Guid homeworkId, CancellationToken ct);
    Task<(bool ok, string? error)> SubmitAnswerAsync(Guid studentId, Guid homeworkId, SubmitHomeworkAnswerRequest req, CancellationToken ct);

    // Teacher review (checked)
    Task<(bool ok, string? error)> CheckAsync(Guid teacherId, Guid homeworkId, CheckHomeworkRequest req, CancellationToken ct);
}
