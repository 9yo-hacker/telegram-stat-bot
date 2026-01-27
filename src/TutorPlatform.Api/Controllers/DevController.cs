using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Contracts.Dev;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/dev")]
public class DevController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly IWebHostEnvironment _env;
    private readonly IJwtTokenService _jwt;
    private readonly IPasswordHasher _hash;

    public DevController(AppDbContext db, IWebHostEnvironment env, IJwtTokenService jwt, IPasswordHasher hash)
    {
        _db = db;
        _env = env;
        _jwt = jwt;
        _hash = hash;
    }

    [HttpPost("seed")]
    public async Task<ActionResult<DevSeedResponse>> Seed(CancellationToken ct)
    {
        if (!_env.IsDevelopment()) return NotFound();

        if (!Request.Headers.TryGetValue("X-Dev-Seed", out var v) || v != "1")
            return NotFound();

        const string teacherEmail = "teacher.dev@local";
        const string studentEmail = "student.dev@local";
        const string studentCode  = "STUDEV0001";

        var now = DateTime.UtcNow;

        // Teacher
        var teacher = await _db.Users.FirstOrDefaultAsync(u => u.Email == teacherEmail, ct);
        if (teacher is null)
        {
            teacher = new UserEntity
            {
                Id = Guid.NewGuid(),
                Email = teacherEmail,
                Name = "Dev Teacher",
                PasswordHash = _hash.Hash("DevPassword123!"),
                Role = UserRole.Teacher,
                CreatedAt = now,
                UpdatedAt = now
            };
            _db.Users.Add(teacher);
            await _db.SaveChangesAsync(ct);
        }

        // Student
        var student = await _db.Users.FirstOrDefaultAsync(u => u.Email == studentEmail, ct);
        if (student is null)
        {
            student = new UserEntity
            {
                Id = Guid.NewGuid(),
                Email = studentEmail,
                Name = "Dev Student",
                PasswordHash = _hash.Hash("DevPassword123!"),
                Role = UserRole.Student,
                StudentCode = studentCode,
                CreatedAt = now,
                UpdatedAt = now
            };
            _db.Users.Add(student);
            await _db.SaveChangesAsync(ct);
        }

        // Course
        var course = await _db.Courses.FirstOrDefaultAsync(c => c.TeacherId == teacher.Id && c.Title == "DEV Course", ct);
        if (course is null)
        {
            course = new CourseEntity
            {
                Id = Guid.NewGuid(),
                TeacherId = teacher.Id,
                Title = "DEV Course",
                Description ="DEV Description",
                DefaultVideoLink = "https://meet.example/dev",
                CreatedAt = now,
                UpdatedAt = now
            };
            _db.Courses.Add(course);
            await _db.SaveChangesAsync(ct);
        }

        // Lesson
        var lesson = await _db.Lessons.FirstOrDefaultAsync(l => l.CourseId == course.Id && l.Title == "DEV Lesson", ct);
        if (lesson is null)
        {
            lesson = new LessonEntity
            {
                Id = Guid.NewGuid(),
                CourseId = course.Id,
                Title = "DEV Lesson",
                MaterialUrl = "https://example.com/material",
                Status = LessonStatus.Published,
                CreatedAt = now,
                UpdatedAt = now
            };
            _db.Lessons.Add(lesson);
            await _db.SaveChangesAsync(ct);
        }

        // Enrollment
        var enrollment = await _db.Enrollments.FirstOrDefaultAsync(e => e.CourseId == course.Id && e.StudentId == student.Id, ct);
        if (enrollment is null)
        {
            enrollment = new EnrollmentEntity
            {
                Id = Guid.NewGuid(),
                CourseId = course.Id,
                StudentId = student.Id,
                Status = EnrollmentStatus.Active,
                CreatedAt = now,
                UpdatedAt = now
            };
            _db.Enrollments.Add(enrollment);
            await _db.SaveChangesAsync(ct);
        }
        else if (enrollment.Status == EnrollmentStatus.Revoked)
        {
            enrollment.Status = EnrollmentStatus.Active;
            enrollment.UpdatedAt = now;
            await _db.SaveChangesAsync(ct);
        }

        var teacherToken = _jwt.CreateAccessToken(teacher);
        var studentToken = _jwt.CreateAccessToken(student);

        return Ok(new DevSeedResponse(
            teacherToken,
            studentToken,
            teacher.Id,
            student.Id,
            course.Id,
            lesson.Id,
            enrollment.Id
        ));
    }
}
