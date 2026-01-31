using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Tests.Shared;

public sealed class TestDb : IAsyncDisposable
{
    private readonly SqliteConnection _conn;
    public AppDbContext Db { get; }

    public TestDb()
    {
        _conn = new SqliteConnection("DataSource=:memory:");
        _conn.Open();

        var opts = new DbContextOptionsBuilder<AppDbContext>()
            .UseSqlite(_conn)
            .EnableSensitiveDataLogging()
            .Options;

        Db = new AppDbContext(opts);
        Db.Database.EnsureCreated();
    }

    public async ValueTask DisposeAsync()
    {
        await Db.DisposeAsync();
        await _conn.DisposeAsync();
    }

    public async Task<(UserEntity teacher, UserEntity student, CourseEntity course, LessonEntity lesson, EnrollmentEntity enrollment)>
        SeedBasicAsync(EnrollmentStatus enrollmentStatus = EnrollmentStatus.Active)
    {
        var now = DateTime.UtcNow;

        var teacher = new UserEntity
        {
            Id = Guid.NewGuid(),
            Email = "t@test.local",
            Name = "Teacher",
            PasswordHash = "hash",
            Role = UserRole.Teacher,
            CreatedAt = now,
            UpdatedAt = now
        };

        var student = new UserEntity
        {
            Id = Guid.NewGuid(),
            Email = "s@test.local",
            Name = "Student",
            PasswordHash = "hash",
            Role = UserRole.Student,
            StudentCode = "123456789",
            CreatedAt = now,
            UpdatedAt = now
        };

        var course = new CourseEntity
        {
            Id = Guid.NewGuid(),
            TeacherId = teacher.Id,
            Title = "Course",
            Description = "Desc",
            DefaultVideoLink = "https://meet.example/default",
            CreatedAt = now,
            UpdatedAt = now
        };

        var lesson = new LessonEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            Title = "Lesson",
            MaterialUrl = "https://example.com/material",
            Status = LessonStatus.Published,
            CreatedAt = now,
            UpdatedAt = now
        };

        var enrollment = new EnrollmentEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            StudentId = student.Id,
            Status = enrollmentStatus,
            CreatedAt = now,
            UpdatedAt = now
        };

        Db.Users.AddRange(teacher, student);
        Db.Courses.Add(course);
        Db.Lessons.Add(lesson);
        Db.Enrollments.Add(enrollment);
        await Db.SaveChangesAsync();

        return (teacher, student, course, lesson, enrollment);
    }
}
