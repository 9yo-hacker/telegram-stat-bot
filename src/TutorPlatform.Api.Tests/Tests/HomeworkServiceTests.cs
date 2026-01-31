using FluentAssertions;
using TutorPlatform.Api.Application.Homework;
using TutorPlatform.Api.Contracts.Homework;
using TutorPlatform.Api.Data.Entities;
using TutorPlatform.Api.Tests.Shared;
using Xunit;

namespace TutorPlatform.Api.Tests.Tests;

public class HomeworkServiceTests
{
    [Fact]
    public async Task Create_Todo_SetsCompletedAtNull()
    {
        await using var tdb = new TestDb();
        var (teacher, _, _, _, enrollment) = await tdb.SeedBasicAsync();

        var svc = new HomeworkService(tdb.Db);

        var req = new CreateHomeworkItemRequest(
            Title: "HW1",
            Description: "desc",
            LinkUrl: "https://example.com",
            DueAt: null,
            Status: HomeworkStatus.Todo
        );

        var (item, err) = await svc.CreateAsync(teacher.Id, enrollment.Id, req, CancellationToken.None);

        err.Should().BeNull();
        item!.CompletedAt.Should().BeNull();
        item.Status.Should().Be(HomeworkStatus.Todo);
    }

    [Fact]
    public async Task Create_DoneOrSkipped_SetsCompletedAt()
    {
        await using var tdb = new TestDb();
        var (teacher, _, _, _, enrollment) = await tdb.SeedBasicAsync();

        var svc = new HomeworkService(tdb.Db);

        var req = new CreateHomeworkItemRequest(
            Title: "HW1",
            Description: null,
            LinkUrl: null,
            DueAt: null,
            Status: HomeworkStatus.Skipped
        );

        var (item, err) = await svc.CreateAsync(teacher.Id, enrollment.Id, req, CancellationToken.None);

        err.Should().BeNull();
        item!.CompletedAt.Should().NotBeNull();
        item.Status.Should().Be(HomeworkStatus.Skipped);
    }

    [Fact]
    public async Task Update_StatusToTodo_ClearsCompletedAt()
    {
        await using var tdb = new TestDb();
        var (teacher, _, _, _, enrollment) = await tdb.SeedBasicAsync();

        // create skipped
        var now = DateTime.UtcNow;
        var entity = new HomeworkItemEntity
        {
            Id = Guid.NewGuid(),
            EnrollmentId = enrollment.Id,
            CreatedByTeacherId = teacher.Id,
            Title = "HW",
            Description = null,
            LinkUrl = null,
            DueAt = null,
            Status = HomeworkStatus.Skipped,
            CompletedAt = now,
            CreatedAt = now,
            UpdatedAt = now
        };
        tdb.Db.HomeworkItems.Add(entity);
        await tdb.Db.SaveChangesAsync();

        var svc = new HomeworkService(tdb.Db);

        var (ok, err) = await svc.UpdateAsync(
            teacher.Id,
            entity.Id,
            new UpdateHomeworkItemRequest(Title: null, Description: null, LinkUrl: null, DueAt: null, Status: HomeworkStatus.Todo),
            CancellationToken.None
        );

        ok.Should().BeTrue();
        err.Should().BeNull();

        var saved = await tdb.Db.HomeworkItems.FindAsync(entity.Id);
        saved!.Status.Should().Be(HomeworkStatus.Todo);
        saved.CompletedAt.Should().BeNull();
    }

    [Fact]
    public async Task Create_Fails_WhenEnrollmentRevoked()
    {
        await using var tdb = new TestDb();
        var (teacher, _, _, _, enrollment) = await tdb.SeedBasicAsync(EnrollmentStatus.Revoked);

        var svc = new HomeworkService(tdb.Db);

        var req = new CreateHomeworkItemRequest(
            Title: "HW",
            Description: null,
            LinkUrl: null,
            DueAt: null,
            Status: null
        );

        var (_, err) = await svc.CreateAsync(teacher.Id, enrollment.Id, req, CancellationToken.None);
        err.Should().Be("revoked");
    }
}
