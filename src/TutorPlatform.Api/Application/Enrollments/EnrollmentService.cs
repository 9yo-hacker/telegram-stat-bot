using System.Linq.Expressions;
using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Contracts.Enrollments;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Enrollments;

public class EnrollmentService : IEnrollmentService
{
    private readonly AppDbContext _db;
    public EnrollmentService(AppDbContext db) => _db = db;

    public async Task<List<EnrollmentResponse>?> GetByCourseAsync(Guid teacherId, Guid courseId, CancellationToken ct)
    {
        var owns = await _db.Courses
            .AnyAsync(c => c.Id == courseId && c.TeacherId == teacherId, ct);

        if (!owns) return null;

        return await _db.Enrollments
            .Where(e => e.CourseId == courseId)
            .OrderByDescending(e => e.CreatedAt)
            .Select(ToDto)
            .ToListAsync(ct);
    }

    public async Task<(EnrollmentResponse? enrollment, string? error)> CreateAsync(
        Guid teacherId, Guid courseId, string studentCode, CancellationToken ct)
    {
        var course = await _db.Courses.FirstOrDefaultAsync(c => c.Id == courseId && c.TeacherId == teacherId, ct);
        if (course is null) return (null, "course_not_found");

        var student = await _db.Users.FirstOrDefaultAsync(u =>
            u.StudentCode == studentCode && u.Role == UserRole.Student, ct);
        if (student is null) return (null, "student_not_found");

        var exists = await _db.Enrollments.AnyAsync(e => e.CourseId == courseId && e.StudentId == student.Id, ct);
        if (exists) return (null, "already_enrolled");

        var now = DateTime.UtcNow;
        var entity = new EnrollmentEntity
        {
            Id = Guid.NewGuid(),
            CourseId = courseId,
            StudentId = student.Id,
            Status = EnrollmentStatus.Active,
            CreatedAt = now,
            UpdatedAt = now
        };

        _db.Enrollments.Add(entity);

        try
        {
            await _db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException)
        {
            // на случай гонки — уникальный индекс
            return (null, "already_enrolled");
        }

        // после SaveChanges Id уже есть, но можно вернуть entity без доп. запроса
        return (new EnrollmentResponse(entity.Id, entity.CourseId, entity.StudentId, entity.Plan, entity.Progress, entity.Status, entity.CreatedAt, entity.UpdatedAt), null);
    }

    public async Task<(bool ok, string? error)> UpdateAsync(Guid teacherId, Guid enrollmentId, UpdateEnrollmentRequest req, CancellationToken ct)
    {
        var e = await _db.Enrollments
            .Include(x => x.Course)
            .FirstOrDefaultAsync(x => x.Id == enrollmentId, ct);

        if (e is null) return (false, "not_found");
        if (e.Course.TeacherId != teacherId) return (false, "not_found");

        e.Plan = req.Plan;
        e.Progress = req.Progress;
        e.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return (true, null);
    }

    public async Task<(bool ok, string? error)> RevokeAsync(Guid teacherId, Guid enrollmentId, CancellationToken ct)
    {
        var e = await _db.Enrollments
            .Include(x => x.Course)
            .FirstOrDefaultAsync(x => x.Id == enrollmentId, ct);

        if (e is null) return (false, "not_found");
        if (e.Course.TeacherId != teacherId) return (false, "not_found");

        if (e.Status == EnrollmentStatus.Revoked) return (true, null); // идемпотентно

        e.Status = EnrollmentStatus.Revoked;
        e.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return (true, null);
    }

    private static readonly Expression<Func<EnrollmentEntity, EnrollmentResponse>> ToDto =
    e => new EnrollmentResponse(
        e.Id, e.CourseId, e.StudentId,
        e.Plan, e.Progress, e.Status,
        e.CreatedAt, e.UpdatedAt);
        
}
