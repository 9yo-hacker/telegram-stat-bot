using Microsoft.EntityFrameworkCore;
using System.Linq.Expressions;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Contracts.Sessions;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Sessions;

public class SessionService : ISessionService
{
    private readonly AppDbContext _db;
    public SessionService(AppDbContext db) => _db = db;

    private static readonly Expression<Func<SessionEntity, SessionResponse>> ToDto =
        s => new SessionResponse(
            s.Id, s.CourseId, s.TeacherId, s.StudentId, s.LessonId,
            s.StartsAt, s.DurationMinutes, s.Status,
            s.VideoLink, s.Notes,
            s.LessonTitleSnapshot, s.LessonMaterialUrlSnapshot,
            s.CreatedAt, s.UpdatedAt
        );

    public async Task<List<SessionResponse>> GetTeacherSessionsAsync(Guid teacherId, Guid? courseId, Guid? studentId, DateTime? from, DateTime? to, int? status, CancellationToken ct)
    {
        var q = _db.Sessions.AsNoTracking().Where(s => s.TeacherId == teacherId);

        if (courseId is not null) q = q.Where(s => s.CourseId == courseId);
        if (studentId is not null) q = q.Where(s => s.StudentId == studentId);
        if (from is not null) q = q.Where(s => s.StartsAt >= from);
        if (to is not null) q = q.Where(s => s.StartsAt < to);
        if (status is not null) q = q.Where(s => (int)s.Status == status);

        return await q.OrderByDescending(s => s.StartsAt).Select(ToDto).ToListAsync(ct);
    }

    public async Task<(SessionResponse? session, string? error)> CreateAsync(Guid teacherId, CreateSessionRequest req, CancellationToken ct)
    {
        // 0) валидация данных: проверка на продолжительность > 0
        if (req.DurationMinutes <= 0) return (null, "invalid_duration");

        // 1) курс должен принадлежать учителю
        var course = await _db.Courses.AsNoTracking()
            .FirstOrDefaultAsync(c => c.Id == req.CourseId && c.TeacherId == teacherId, ct);
        if (course is null) return (null, "course_not_found");

        // 2) должен быть Active enrollment на (courseId, studentId)
        var enrollment = await _db.Enrollments.AsNoTracking()
            .FirstOrDefaultAsync(e => e.CourseId == req.CourseId && e.StudentId == req.StudentId, ct);

        if (enrollment is null) return (null, "enrollment_not_found");             // QA #20
        if (enrollment.Status == EnrollmentStatus.Revoked) return (null, "revoked"); // QA #21

        // 3) если lessonId задан — он должен быть из этого course
        if (req.LessonId is not null)
        {
            var okLesson = await _db.Lessons.AsNoTracking()
                .AnyAsync(l => l.Id == req.LessonId && l.CourseId == req.CourseId, ct);
            if (!okLesson) return (null, "lesson_wrong_course"); // QA #22
        }

        // 4) создать сессию
        var now = DateTime.UtcNow;
        var entity = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = req.CourseId,
            TeacherId = teacherId,
            StudentId = req.StudentId,
            LessonId = req.LessonId,
            StartsAt = req.StartsAt,
            DurationMinutes = req.DurationMinutes,
            VideoLink = req.VideoLink,
            Notes = req.Notes,
            Status = SessionStatus.Planned,
            CreatedAt = now,
            UpdatedAt = now
        };

        _db.Sessions.Add(entity);
        await _db.SaveChangesAsync(ct);

        var dto = new SessionResponse(
            entity.Id, entity.CourseId, entity.TeacherId, entity.StudentId, entity.LessonId,
            entity.StartsAt, entity.DurationMinutes, entity.Status,
            entity.VideoLink, entity.Notes,
            entity.LessonTitleSnapshot, entity.LessonMaterialUrlSnapshot,
            entity.CreatedAt, entity.UpdatedAt
        );

        return (dto, null);
    }

    public async Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid sessionId, UpdateSessionRequest req, CancellationToken ct)
    {
        var s = await _db.Sessions.FirstOrDefaultAsync(x => x.Id == sessionId, ct);
        if (s is null || s.TeacherId != teacherId) return (false, "not_found");

        // Validation
        if (req.DurationMinutes is not null && req.DurationMinutes.Value <= 0)
            return (false, "invalid_duration");

        // Done нельзя менять через PUT (только /complete)
        if (req.Status == SessionStatus.Done) return (false, "done_via_complete_only");

        // Если lesson меняют — проверка “lesson belongs to course”
        if (req.LessonId is not null)
        {
            var okLesson = await _db.Lessons.AsNoTracking()
                .AnyAsync(l => l.Id == req.LessonId && l.CourseId == s.CourseId, ct);
            if (!okLesson) return (false, "lesson_wrong_course");
        }

        if (req.StartsAt is not null) s.StartsAt = req.StartsAt.Value;
        if (req.DurationMinutes is not null) s.DurationMinutes = req.DurationMinutes.Value;
        if (req.LessonId is not null || req.LessonId is null) s.LessonId = req.LessonId; // если хочешь разрешить “снять урок”, оставь так
        if (req.VideoLink is not null || req.VideoLink is null) s.VideoLink = req.VideoLink;
        if (req.Notes is not null || req.Notes is null) s.Notes = req.Notes;

        if (req.Status is not null)
        {
            // Разрешаем Planned <-> Canceled
            s.Status = req.Status.Value;
        }

        s.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return (true, null);
    }

    public async Task<(bool ok, string? error)> CompleteAsync(Guid teacherId, Guid sessionId, CancellationToken ct)
    {
        var s = await _db.Sessions.FirstOrDefaultAsync(x => x.Id == sessionId, ct);
        if (s is null || s.TeacherId != teacherId) return (false, "not_found");

        if (s.Status == SessionStatus.Done) return (true, null); // идемпотентно
        if (s.Status == SessionStatus.Canceled) return (false, "cannot_complete_canceled");

        // snapshot
        if (s.LessonId is not null)
        {
            var lesson = await _db.Lessons.AsNoTracking()
                .FirstOrDefaultAsync(l => l.Id == s.LessonId && l.CourseId == s.CourseId, ct);

            // если урок удалён/не найден — снимок будет пустым, но Done всё равно можно поставить
            if (lesson is not null)
            {
                s.LessonTitleSnapshot = lesson.Title;
                s.LessonMaterialUrlSnapshot = lesson.MaterialUrl;
            }
        }

        s.Status = SessionStatus.Done;
        s.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return (true, null);
    }

    public async Task<List<MySessionListItemResponse>> GetMySessionsAsync(Guid studentId, CancellationToken ct)
    {
        return await _db.Sessions.AsNoTracking()
            .Where(s => s.StudentId == studentId)
            .OrderByDescending(s => s.StartsAt)
            .Select(s => new MySessionListItemResponse(s.Id, s.StartsAt, s.DurationMinutes, s.Status))
            .ToListAsync(ct);
    }

    public async Task<MySessionDetailsResponse?> GetMySessionAsync(Guid studentId, Guid sessionId, CancellationToken ct)
    {
        // Planned: live lesson materialUrl
        // Done: snapshot fields

        var row = await _db.Sessions.AsNoTracking()
            .Where(s => s.Id == sessionId && s.StudentId == studentId)
            .Select(s => new
            {
                s.Id, s.StartsAt, s.DurationMinutes, s.Status,
                s.VideoLink,
                CourseDefaultVideoLink = s.Course.DefaultVideoLink,
                LessonMaterialUrlLive = s.Lesson != null ? s.Lesson.MaterialUrl : null,
                s.LessonTitleSnapshot,
                s.LessonMaterialUrlSnapshot
            })
            .FirstOrDefaultAsync(ct);

        if (row is null) return null;

        var effective = row.VideoLink ?? row.CourseDefaultVideoLink;

        return new MySessionDetailsResponse(
            row.Id,
            row.StartsAt,
            row.DurationMinutes,
            row.Status,
            effective,
            row.Status == SessionStatus.Planned ? row.LessonMaterialUrlLive : null,
            row.LessonTitleSnapshot,
            row.LessonMaterialUrlSnapshot
        );
    }
}
