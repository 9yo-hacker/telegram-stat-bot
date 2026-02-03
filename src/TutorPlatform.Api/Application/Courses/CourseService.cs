using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Contracts.Courses;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Application.Courses;

public class CourseService : ICourseService
{
    private readonly AppDbContext _db;

    public CourseService(AppDbContext db) => _db = db;

    public async Task<List<CourseListItemResponse>> GetMyCoursesAsync(Guid teacherId, CancellationToken ct)
    {
        return await _db.Courses
            .Where(c => c.TeacherId == teacherId)
            .OrderByDescending(c => c.UpdatedAt)
            .Select(c => new CourseListItemResponse(
                c.Id, c.Title, c.Status, c.CreatedAt, c.UpdatedAt
            ))
            .ToListAsync(ct);
    }

    public async Task<CourseResponse?> GetMyCourseAsync(Guid teacherId, Guid courseId, CancellationToken ct)
    {
        return await _db.Courses
            .Where(c => c.Id == courseId && c.TeacherId == teacherId)
            .Select(c => new CourseResponse(
                c.Id, c.Title, c.Description, c.DefaultVideoLink, c.Status, c.CreatedAt, c.UpdatedAt
            ))
            .FirstOrDefaultAsync(ct);
    }

    public async Task<CourseResponse> CreateAsync(Guid teacherId, CreateCourseRequest req, CancellationToken ct)
    {
        Validate(req.Title, req.Description, req.DefaultVideoLink);

        var now = DateTime.UtcNow;

        var course = new CourseEntity

        {
            Id = Guid.NewGuid(),
            TeacherId = teacherId,
            Title = req.Title.Trim(),
            Description = req.Description.Trim(),
            DefaultVideoLink = string.IsNullOrWhiteSpace(req.DefaultVideoLink) ? null : req.DefaultVideoLink.Trim(),
            Status = req.Status ?? CourseStatus.Draft,
            CreatedAt = now,
            UpdatedAt = now,
        };

        _db.Courses.Add(course);
        await _db.SaveChangesAsync(ct);

        return new CourseResponse(course.Id, course.Title, course.Description, course.DefaultVideoLink,
            course.Status, course.CreatedAt, course.UpdatedAt);
    }

    public async Task<bool> UpdateAsync(Guid teacherId, Guid courseId, UpdateCourseRequest req, CancellationToken ct)
    {
        ValidatePatch(req);

        var course = await _db.Courses
            .FirstOrDefaultAsync(c => c.Id == courseId && c.TeacherId == teacherId, ct);

        if (course is null) return false;

        if (req.Title is not null)
            course.Title = req.Title.Trim();

        if (req.Description is not null)
            course.Description = req.Description.Trim();

        if (req.DefaultVideoLink is not null)
            course.DefaultVideoLink = string.IsNullOrWhiteSpace(req.DefaultVideoLink)
                ? null
                : req.DefaultVideoLink.Trim();

        if (req.Status is not null)
            course.Status = req.Status.Value;

        course.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return true;
    }


    public async Task<bool> ArchiveAsync(Guid teacherId, Guid courseId, CancellationToken ct)
    {
        var course = await _db.Courses
            .FirstOrDefaultAsync(c => c.Id == courseId && c.TeacherId == teacherId, ct);

        if (course is null) return false;

        course.Status = CourseStatus.Archived;
        course.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync(ct);
        return true;
    }

    // Student side

    public async Task<List<CourseListItemResponse>> GetMyCoursesAsStudentAsync(Guid studentId, CancellationToken ct)
    {
        // only courses where student has an Active enrollment
        return await _db.Enrollments.AsNoTracking()
            .Where(e => e.StudentId == studentId && e.Status == EnrollmentStatus.Active)
            .OrderByDescending(e => e.UpdatedAt)
            .Select(e => new CourseListItemResponse(
                e.Course.Id,
                e.Course.Title,
                e.Course.Status,
                e.Course.CreatedAt,
                e.Course.UpdatedAt
            ))
            .Distinct()
            .ToListAsync(ct);
    }

    public async Task<CourseResponse?> GetMyCourseAsStudentAsync(Guid studentId, Guid courseId, CancellationToken ct)
    {
        // access via enrollment; do not leak course existence
        return await _db.Enrollments.AsNoTracking()
            .Where(e => e.StudentId == studentId && e.Status == EnrollmentStatus.Active && e.CourseId == courseId)
            .Select(e => new CourseResponse(
                e.Course.Id,
                e.Course.Title,
                e.Course.Description,
                e.Course.DefaultVideoLink,
                e.Course.Status,
                e.Course.CreatedAt,
                e.Course.UpdatedAt
            ))
            .FirstOrDefaultAsync(ct);
    }

    private static void Validate(string title, string description, string? defaultVideoLink)
    {
        if (string.IsNullOrWhiteSpace(title) || title.Trim().Length > 200)
            throw new ArgumentException("Title is required and must be <= 200 chars.");

        if (string.IsNullOrWhiteSpace(description) || description.Trim().Length > 2000)
            throw new ArgumentException("Description is required and must be <= 2000 chars.");

        if (defaultVideoLink is not null && defaultVideoLink.Length > 2000)
            throw new ArgumentException("DefaultVideoLink must be <= 2000 chars.");
    }

    private static void ValidatePatch(UpdateCourseRequest req)
    {
        if (req.Title is not null && string.IsNullOrWhiteSpace(req.Title))
            throw new CannotUnloadAppDomainException("Title cannot be empty.");

        if (req.Description is not null && string.IsNullOrWhiteSpace(req.Description))
            throw new CannotUnloadAppDomainException("Description cannot be empty.");

        if (req.DefaultVideoLink is not null && !string.IsNullOrWhiteSpace(req.DefaultVideoLink))
        {
            var v = req.DefaultVideoLink.Trim();
            if (v.Length > 2000)
                throw new CannotUnloadAppDomainException("DefaultVideoLink is too long.");
        }

        if (req.Status is not null && !Enum.IsDefined(typeof(CourseStatus), req.Status.Value))
            throw new CannotUnloadAppDomainException("Status is invalid.");

        if (req.Title is null && req.Description is null && req.DefaultVideoLink is null && req.Status is null)
            throw new CannotUnloadAppDomainException("No fields to update.");
    }
}