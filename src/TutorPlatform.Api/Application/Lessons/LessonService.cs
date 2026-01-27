using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Common.Errors;
using TutorPlatform.Api.Contracts.Lessons;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Lessons;

public sealed class LessonService : ILessonService
{
    private readonly AppDbContext _db;

    public LessonService(AppDbContext db)
    {
        _db = db;
    }

    public async Task<IReadOnlyList<LessonResponse>> GetListAsync(
        Guid teacherId,
        Guid courseId,
        CancellationToken ct)
    {
        // Сначала проверим владение курсом, чтобы не светить чужие данные
        var ownsCourse = await _db.Courses
            .AnyAsync(c => c.Id == courseId && c.TeacherId == teacherId, ct);

        if (!ownsCourse)
            return Array.Empty<LessonResponse>(); // или можно бросать и в контроллере вернуть 404

        var lessons = await _db.Lessons
            .Where(l => l.CourseId == courseId)
            .OrderByDescending(l => l.UpdatedAt)
            .Select(l => new LessonResponse(
                l.Id,
                l.CourseId,
                l.Title,
                l.MaterialUrl,
                l.Status
            ))
            .ToListAsync(ct);

        return lessons;
    }

    public async Task<LessonResponse?> GetAsync(
        Guid teacherId,
        Guid lessonId,
        CancellationToken ct)
    {
        return await _db.Lessons
            .Where(l => l.Id == lessonId && l.Course.TeacherId == teacherId)
            .Select(l => new LessonResponse(
                l.Id,
                l.CourseId,
                l.Title,
                l.MaterialUrl,
                l.Status
            ))
            .FirstOrDefaultAsync(ct);
    }

    public async Task<Guid> CreateAsync(
        Guid teacherId,
        Guid courseId,
        CreateLessonRequest req,
        CancellationToken ct)
    {
        ValidateCreate(req);

        var course = await _db.Courses
            .FirstOrDefaultAsync(c => c.Id == courseId && c.TeacherId == teacherId, ct);

        if (course is null)
            throw new DomainException("Course not found."); // контроллер -> 404

        var now = DateTime.UtcNow;

        var lesson = new LessonEntity
        {
            Id = Guid.NewGuid(),
            CourseId = courseId,
            Title = req.Title.Trim(),
            MaterialUrl = NormalizeUrl(req.MaterialUrl),
            Status = req.Status,
            CreatedAt = now,
            UpdatedAt = now
        };

        _db.Lessons.Add(lesson);
        await _db.SaveChangesAsync(ct);

        return lesson.Id;
    }

    public async Task<bool> UpdateAsync(
        Guid teacherId,
        Guid lessonId,
        UpdateLessonRequest req,
        CancellationToken ct)
    {
        ValidatePatch(req);

        var lesson = await _db.Lessons
            .FirstOrDefaultAsync(l => l.Id == lessonId && l.Course.TeacherId == teacherId, ct);

        if (lesson is null) return false;

        if (req.Title is not null)
            lesson.Title = req.Title.Trim();

        if (req.MaterialUrl is not null)
            lesson.MaterialUrl = NormalizeUrl(req.MaterialUrl);

        if (req.Status is not null)
            lesson.Status = req.Status.Value;

        lesson.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return true;
    }

    // -------------------------
    // Validation helpers
    // -------------------------

    private static void ValidateCreate(CreateLessonRequest req)
    {
        if (string.IsNullOrWhiteSpace(req.Title))
            throw new DomainException("Title cannot be empty.");

        if (req.Title.Trim().Length > 256)
            throw new DomainException("Title is too long.");

        if (!Enum.IsDefined(typeof(LessonStatus), req.Status))
            throw new DomainException("Status is invalid.");

        if (req.MaterialUrl is not null && req.MaterialUrl.Trim().Length > 2048)
            throw new DomainException("MaterialUrl is too long.");
    }

    private static void ValidatePatch(UpdateLessonRequest req)
    {
        // запретим пустые строки для Title, если поле передали
        if (req.Title is not null)
        {
            if (string.IsNullOrWhiteSpace(req.Title))
                throw new DomainException("Title cannot be empty.");

            if (req.Title.Trim().Length > 256)
                throw new DomainException("Title is too long.");
        }

        // MaterialUrl: разрешаем очистку ("" -> null), но ограничим длину если не пусто
        if (req.MaterialUrl is not null && !string.IsNullOrWhiteSpace(req.MaterialUrl))
        {
            if (req.MaterialUrl.Trim().Length > 2048)
                throw new DomainException("MaterialUrl is too long.");
        }

        if (req.Status is not null && !Enum.IsDefined(typeof(LessonStatus), req.Status.Value))
            throw new DomainException("Status is invalid.");

        // запретим пустой запрос {}
        if (req.Title is null && req.MaterialUrl is null && req.Status is null)
            throw new DomainException("No fields to update.");
    }

    private static string? NormalizeUrl(string? url)
        => string.IsNullOrWhiteSpace(url) ? null : url.Trim();
}
