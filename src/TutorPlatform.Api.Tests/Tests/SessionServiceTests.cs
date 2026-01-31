using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Sessions;
using TutorPlatform.Api.Contracts.Sessions;
using TutorPlatform.Api.Data.Entities;
using TutorPlatform.Api.Tests.Shared;
using Xunit;

namespace TutorPlatform.Api.Tests.Tests;

public class SessionServiceTests
{
    [Fact]
    public async Task Create_AllowsStartsAtInPast_MvpRule()
    {
        await using var tdb = new TestDb();
        var (teacher, student, course, lesson, _) = await tdb.SeedBasicAsync();

        var svc = new SessionService(tdb.Db);

        var req = new CreateSessionRequest(
            course.Id,
            student.Id,
            StartsAt: DateTime.UtcNow.AddDays(-10), // важно: в прошлом разрешено
            DurationMinutes: 60,
            LessonId: lesson.Id,
            VideoLink: null,
            Notes: "past ok"
        );

        var (dto, err) = await svc.CreateAsync(teacher.Id, req, CancellationToken.None);

        err.Should().BeNull();
        dto.Should().NotBeNull();
        dto!.Status.Should().Be(SessionStatus.Planned);
        dto.StartsAt.Should().Be(req.StartsAt);
    }

    [Fact]
    public async Task Create_Fails_WhenEnrollmentRevoked()
    {
        await using var tdb = new TestDb();
        var (teacher, student, course, lesson, _) = await tdb.SeedBasicAsync(EnrollmentStatus.Revoked);

        var svc = new SessionService(tdb.Db);

        var req = new CreateSessionRequest(
            course.Id, student.Id, DateTime.UtcNow.AddDays(1), 60, lesson.Id, null, null
        );

        var (_, err) = await svc.CreateAsync(teacher.Id, req, CancellationToken.None);

        err.Should().Be("revoked");
    }

    [Fact]
    public async Task Complete_SetsSnapshot_FromLesson()
    {
        await using var tdb = new TestDb();
        var (teacher, student, course, lesson, _) = await tdb.SeedBasicAsync();

        // create session
        var s = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            TeacherId = teacher.Id,
            StudentId = student.Id,
            LessonId = lesson.Id,
            StartsAt = DateTime.UtcNow.AddHours(1),
            DurationMinutes = 45,
            Status = SessionStatus.Planned,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };
        tdb.Db.Sessions.Add(s);
        await tdb.Db.SaveChangesAsync();

        var svc = new SessionService(tdb.Db);

        var (ok, err) = await svc.CompleteAsync(teacher.Id, s.Id, CancellationToken.None);

        ok.Should().BeTrue();
        err.Should().BeNull();

        var saved = await tdb.Db.Sessions.FindAsync(s.Id);
        saved!.Status.Should().Be(SessionStatus.Done);
        saved.LessonTitleSnapshot.Should().Be(lesson.Title);
        saved.LessonMaterialUrlSnapshot.Should().Be(lesson.MaterialUrl);
    }

    [Fact]
    public async Task Complete_IsIdempotent_WhenAlreadyDone()
    {
        await using var tdb = new TestDb();
        var (teacher, student, course, lesson, _) = await tdb.SeedBasicAsync();

        var s = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            TeacherId = teacher.Id,
            StudentId = student.Id,
            LessonId = lesson.Id,
            StartsAt = DateTime.UtcNow,
            DurationMinutes = 30,
            Status = SessionStatus.Done,
            LessonTitleSnapshot = "snap",
            LessonMaterialUrlSnapshot = "snap-url",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };
        tdb.Db.Sessions.Add(s);
        await tdb.Db.SaveChangesAsync();

        var svc = new SessionService(tdb.Db);

        var (ok, err) = await svc.CompleteAsync(teacher.Id, s.Id, CancellationToken.None);

        ok.Should().BeTrue();
        err.Should().BeNull();

        var saved = await tdb.Db.Sessions.AsNoTracking().FirstAsync(x => x.Id == s.Id);
        saved.LessonTitleSnapshot.Should().Be("snap"); // не должен затереться
    }

    [Fact]
    public async Task GetMySession_VideoLinkEffective_UsesSessionOverride_ElseCourseDefault()
    {
        await using var tdb = new TestDb();
        var (teacher, student, course, lesson, _) = await tdb.SeedBasicAsync();

        var s1 = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            TeacherId = teacher.Id,
            StudentId = student.Id,
            LessonId = lesson.Id,
            StartsAt = DateTime.UtcNow,
            DurationMinutes = 30,
            Status = SessionStatus.Planned,
            VideoLink = null,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        var s2 = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            TeacherId = teacher.Id,
            StudentId = student.Id,
            LessonId = lesson.Id,
            StartsAt = DateTime.UtcNow,
            DurationMinutes = 30,
            Status = SessionStatus.Planned,
            VideoLink = "https://meet.example/override",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        tdb.Db.Sessions.AddRange(s1, s2);
        await tdb.Db.SaveChangesAsync();

        var svc = new SessionService(tdb.Db);

        var d1 = await svc.GetMySessionAsync(student.Id, s1.Id, CancellationToken.None);
        d1!.VideoLinkEffective.Should().Be(course.DefaultVideoLink);

        var d2 = await svc.GetMySessionAsync(student.Id, s2.Id, CancellationToken.None);
        d2!.VideoLinkEffective.Should().Be("https://meet.example/override");
    }

    [Fact]
    public async Task GetMySession_Planned_ReturnsLiveMaterialUrl_DoneReturnsSnapshotOnly()
    {
        await using var tdb = new TestDb();
        var (teacher, student, course, lesson, _) = await tdb.SeedBasicAsync();

        var planned = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            TeacherId = teacher.Id,
            StudentId = student.Id,
            LessonId = lesson.Id,
            StartsAt = DateTime.UtcNow,
            DurationMinutes = 30,
            Status = SessionStatus.Planned,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        var done = new SessionEntity
        {
            Id = Guid.NewGuid(),
            CourseId = course.Id,
            TeacherId = teacher.Id,
            StudentId = student.Id,
            LessonId = lesson.Id,
            StartsAt = DateTime.UtcNow,
            DurationMinutes = 30,
            Status = SessionStatus.Done,
            LessonTitleSnapshot = "snap-title",
            LessonMaterialUrlSnapshot = "snap-url",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        tdb.Db.Sessions.AddRange(planned, done);
        await tdb.Db.SaveChangesAsync();

        var svc = new SessionService(tdb.Db);

        var p = await svc.GetMySessionAsync(student.Id, planned.Id, CancellationToken.None);
        p!.LiveLessonMaterialUrl.Should().Be(lesson.MaterialUrl);
        p.LessonMaterialUrlSnapshot.Should().BeNull();

        var d = await svc.GetMySessionAsync(student.Id, done.Id, CancellationToken.None);
        d!.LiveLessonMaterialUrl.Should().BeNull();
        d.LessonTitleSnapshot.Should().Be("snap-title");
        d.LessonMaterialUrlSnapshot.Should().Be("snap-url");
    }
}
