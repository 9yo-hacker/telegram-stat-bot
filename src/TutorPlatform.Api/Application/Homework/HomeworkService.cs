using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Contracts.Homework;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Homework;

public class HomeworkService : IHomeworkService
{
    private readonly AppDbContext _db;
    public HomeworkService(AppDbContext db) => _db = db;

    private static HomeworkItemResponse ToDto(HomeworkItemEntity h) =>
        new(h.Id, h.EnrollmentId, h.CreatedByTeacherId, h.Title, h.Description, h.LinkUrl, h.DueAt,
            h.Status, h.CompletedAt, h.CreatedAt, h.UpdatedAt);

    public async Task<List<HomeworkItemResponse>?> GetByEnrollmentAsync(Guid teacherId, Guid enrollmentId, CancellationToken ct)
    {
        var ok = await _db.Enrollments.AsNoTracking()
            .AnyAsync(e => e.Id == enrollmentId && e.Course.TeacherId == teacherId, ct);
        if (!ok) return null;

        var list = await _db.HomeworkItems.AsNoTracking()
            .Where(h => h.EnrollmentId == enrollmentId)
            .OrderBy(h => h.DueAt == null)     // null last
            .ThenBy(h => h.DueAt)
            .ThenByDescending(h => h.CreatedAt)
            .ToListAsync(ct);

        return list.Select(ToDto).ToList();
    }

    public async Task<(HomeworkItemResponse? item, string? error)> CreateAsync(Guid teacherId, Guid enrollmentId, CreateHomeworkItemRequest req, CancellationToken ct)
    {
        var enrollment = await _db.Enrollments
            .Include(e => e.Course)
            .FirstOrDefaultAsync(e => e.Id == enrollmentId, ct);

        if (enrollment is null) return (null, "not_found");
        if (enrollment.Course.TeacherId != teacherId) return (null, "not_found");

        if (enrollment.Status == EnrollmentStatus.Revoked) return (null, "revoked");

        var now = DateTime.UtcNow;

        var status = req.Status ?? HomeworkStatus.Todo;
        DateTime? completedAt = status == HomeworkStatus.Todo ? null : now;

        var entity = new HomeworkItemEntity
        {
            Id = Guid.NewGuid(),
            EnrollmentId = enrollmentId,
            CreatedByTeacherId = teacherId,
            Title = req.Title,
            Description = req.Description,
            LinkUrl = req.LinkUrl,
            DueAt = req.DueAt,
            Status = status,
            CompletedAt = completedAt,
            CreatedAt = now,
            UpdatedAt = now
        };

        _db.HomeworkItems.Add(entity);
        await _db.SaveChangesAsync(ct);

        return (ToDto(entity), null);
    }

    public async Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid homeworkId, UpdateHomeworkItemRequest req, CancellationToken ct)
    {
        var h = await _db.HomeworkItems
            .Include(x => x.Enrollment)
            .ThenInclude(e => e.Course)
            .FirstOrDefaultAsync(x => x.Id == homeworkId, ct);

        if (h is null) return (false, "not_found");
        if (h.Enrollment.Course.TeacherId != teacherId) return (false, "not_found");

        if (req.Title is not null) h.Title = req.Title;
        if (req.Description is not null) h.Description = req.Description;
        if (req.LinkUrl is not null) h.LinkUrl = req.LinkUrl;
        if (req.DueAt is not null) h.DueAt = req.DueAt;

        if (req.Status is not null)
        {
            h.Status = req.Status.Value;

            if (h.Status == HomeworkStatus.Todo)
                h.CompletedAt = null;
            else
                h.CompletedAt ??= DateTime.UtcNow;
        }

        h.UpdatedAt = DateTime.UtcNow;
        await _db.SaveChangesAsync(ct);

        return (true, null);
    }

    public async Task<(bool ok, string? error)> DeleteAsync(Guid teacherId, Guid homeworkId, CancellationToken ct)
    {
        var h = await _db.HomeworkItems
            .Include(x => x.Enrollment)
            .ThenInclude(e => e.Course)
            .FirstOrDefaultAsync(x => x.Id == homeworkId, ct);

        if (h is null) return (false, "not_found");
        if (h.Enrollment.Course.TeacherId != teacherId) return (false, "not_found");

        _db.HomeworkItems.Remove(h);
        await _db.SaveChangesAsync(ct);
        return (true, null);
    }
}
