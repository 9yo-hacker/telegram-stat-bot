using TutorPlatform.Api.Contracts.Lessons;

public interface ILessonService
{
    Task<IReadOnlyList<LessonResponse>> GetListAsync(Guid teacherId, Guid courseId, CancellationToken ct);
    Task<LessonResponse?> GetAsync(Guid teacherId, Guid lessonId, CancellationToken ct);
    Task<Guid> CreateAsync(Guid teacherId, Guid courseId, CreateLessonRequest req, CancellationToken ct);
    Task<bool> UpdateAsync(Guid teacherId, Guid lessonId, UpdateLessonRequest req, CancellationToken ct);
}
