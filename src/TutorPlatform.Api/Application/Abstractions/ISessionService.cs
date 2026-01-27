using TutorPlatform.Api.Contracts.Sessions;

namespace TutorPlatform.Api.Application.Abstractions;

public interface ISessionService
{
    Task<List<SessionResponse>> GetTeacherSessionsAsync(Guid teacherId, Guid? courseId, Guid? studentId, DateTime? from, DateTime? to, int? status, CancellationToken ct);
    Task<(SessionResponse? session, string? error)> CreateAsync(Guid teacherId, CreateSessionRequest req, CancellationToken ct);
    Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid sessionId, UpdateSessionRequest req, CancellationToken ct);
    Task<(bool ok, string? error)> CompleteAsync(Guid teacherId, Guid sessionId, CancellationToken ct);
    Task<List<MySessionListItemResponse>> GetMySessionsAsync(Guid studentId, CancellationToken ct);
    Task<MySessionDetailsResponse?> GetMySessionAsync(Guid studentId, Guid sessionId, CancellationToken ct);
}
