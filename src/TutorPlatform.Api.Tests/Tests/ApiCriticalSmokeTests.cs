using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Contracts.Dev;
using TutorPlatform.Api.Contracts.Sessions;
using TutorPlatform.Api.Data;
using TutorPlatform.Api.Data.Entities;
using TutorPlatform.Api.Tests.Shared;
using Xunit;

namespace TutorPlatform.Api.Tests.Tests;

public class ApiCriticalRegressionPackTests : IClassFixture<ApiFactory>
{
    private readonly ApiFactory _factory;

    // enum as string
    private static readonly JsonSerializerOptions JsonOpts = new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) }
    };

    public ApiCriticalRegressionPackTests(ApiFactory factory) => _factory = factory;

    // Helpers

    private async Task<DevSeedResponse> SeedAsync(HttpClient client)
    {
        var req = new HttpRequestMessage(HttpMethod.Post, "/api/dev/seed");
        req.Headers.Add("X-Dev-Seed", "1");

        var resp = await client.SendAsync(req);
        if (resp.StatusCode != HttpStatusCode.OK)
        {
            var body = await resp.Content.ReadAsStringAsync();
            throw new Exception($"Seed failed: {(int)resp.StatusCode} {resp.StatusCode}\n{body}");
        }

        var seed = await resp.Content.ReadFromJsonAsync<DevSeedResponse>(JsonOpts);
        seed.Should().NotBeNull();
        return seed!;
    }

    private static void SetBearer(HttpClient client, string token) =>
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);

    private async Task<SessionResponse> CreateSessionAsync(HttpClient client, DevSeedResponse seed, string notes = "smoke")
    {
        var req = new CreateSessionRequest(
            seed.CourseId,
            seed.StudentId,
            DateTime.UtcNow.AddMinutes(30),
            60,
            seed.LessonId,
            null,
            notes
        );

        var resp = await client.PostAsJsonAsync("/api/sessions", req);
        resp.StatusCode.Should().BeOneOf(HttpStatusCode.OK, HttpStatusCode.Created);

        var dto = await resp.Content.ReadFromJsonAsync<SessionResponse>(JsonOpts);
        dto.Should().NotBeNull();
        return dto!;
    }

    // Critical pack

    [Trait("Critical", "true")]
    [Fact]
    public async Task Swagger_ShouldBeAvailable()
    {
        var client = _factory.CreateClient();
        var resp = await client.GetAsync("/swagger/index.html");
        resp.StatusCode.Should().Be(HttpStatusCode.OK);
    }

    [Trait("Critical", "true")]
    [Fact]
    public async Task CriticalFlow_Seed_Create_Planned_ShowsLiveMaterial_Complete_ShowsSnapshot()
    {
        var client = _factory.CreateClient();
        var seed = await SeedAsync(client);

        // Teacher creates session
        SetBearer(client, seed.TeacherToken);
        var created = await CreateSessionAsync(client, seed, "critical-flow");

        // Student reads PLANNED details: live material есть, snapshot пуст
        SetBearer(client, seed.StudentToken);
        var plannedResp = await client.GetAsync($"/api/my/sessions/{created.Id}");
        plannedResp.StatusCode.Should().Be(HttpStatusCode.OK);

        var planned = await plannedResp.Content.ReadFromJsonAsync<MySessionDetailsResponse>(JsonOpts);
        planned.Should().NotBeNull();

        planned!.Status.Should().Be(SessionStatus.Planned);
        planned.LiveLessonMaterialUrl.Should().NotBeNull("planned must expose live lesson material url");
        planned.LessonMaterialUrlSnapshot.Should().BeNull("planned should not expose snapshot material url");
        planned.VideoLinkEffective.Should().NotBeNull("must always provide effective video link");

        // Complete (teacher)
        SetBearer(client, seed.TeacherToken);
        var completeResp = await client.PostAsync($"/api/sessions/{created.Id}/complete", null);
        completeResp.StatusCode.Should().BeOneOf(HttpStatusCode.NoContent, HttpStatusCode.OK);

        // Student reads DONE details: live material null, snapshot заполнен
        SetBearer(client, seed.StudentToken);
        var doneResp = await client.GetAsync($"/api/my/sessions/{created.Id}");
        doneResp.StatusCode.Should().Be(HttpStatusCode.OK);

        var done = await doneResp.Content.ReadFromJsonAsync<MySessionDetailsResponse>(JsonOpts);
        done.Should().NotBeNull();

        done!.Status.Should().Be(SessionStatus.Done);
        done.LiveLessonMaterialUrl.Should().BeNull("done must not expose live lesson material url");
        done.LessonTitleSnapshot.Should().NotBeNull("done must have lesson title snapshot");
        done.LessonMaterialUrlSnapshot.Should().NotBeNull("done must have lesson material url snapshot");
        done.VideoLinkEffective.Should().NotBeNull("effective video link must still exist");
    }

    [Trait("Critical", "true")]
    [Fact]
    public async Task Complete_ShouldBeIdempotent()
    {
        var client = _factory.CreateClient();
        var seed = await SeedAsync(client);

        // Create session
        SetBearer(client, seed.TeacherToken);
        var created = await CreateSessionAsync(client, seed, "idempotent");

        // Complete 1
        var c1 = await client.PostAsync($"/api/sessions/{created.Id}/complete", null);
        c1.StatusCode.Should().BeOneOf(HttpStatusCode.NoContent, HttpStatusCode.OK);

        // Complete 2 must not fail
        var c2 = await client.PostAsync($"/api/sessions/{created.Id}/complete", null);
        c2.StatusCode.Should().BeOneOf(HttpStatusCode.NoContent, HttpStatusCode.OK);
    }

    [Trait("Critical", "true")]
    [Fact]
    public async Task EnrollmentRevoked_ShouldBlockCreateSession()
    {
        var client = _factory.CreateClient();
        var seed = await SeedAsync(client);

        // revoke enrollment directly in DB (we own the in-memory db in tests)
        using (var scope = _factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var enr = await db.Enrollments.FindAsync(seed.EnrollmentId);
            enr.Should().NotBeNull();
            enr!.Status = EnrollmentStatus.Revoked;
            await db.SaveChangesAsync();
        }

        SetBearer(client, seed.TeacherToken);

        var req = new CreateSessionRequest(
            seed.CourseId,
            seed.StudentId,
            DateTime.UtcNow.AddHours(3),
            60,
            seed.LessonId,
            null,
            "should fail"
        );

        var resp = await client.PostAsJsonAsync("/api/sessions", req);

        resp.StatusCode.Should().NotBe(HttpStatusCode.OK);
        resp.StatusCode.Should().NotBe(HttpStatusCode.Created);
    }

    [Trait("Critical", "true")]
    [Fact]
    public async Task Student_CannotReadOtherStudentsSession()
    {
        var client = _factory.CreateClient();
        var seed = await SeedAsync(client);

        // teacher creates session for seed.StudentId
        SetBearer(client, seed.TeacherToken);
        var created = await CreateSessionAsync(client, seed, "privacy");

        // create other student + token
        string otherToken;
        using (var scope = _factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var jwt = scope.ServiceProvider.GetRequiredService<IJwtTokenService>();
            var hash = scope.ServiceProvider.GetRequiredService<IPasswordHasher>();

            var now = DateTime.UtcNow;
            var other = new UserEntity
            {
                Id = Guid.NewGuid(),
                Email = "other.student@local",
                Name = "Other Student",
                PasswordHash = hash.Hash("DevPassword123!"),
                Role = UserRole.Student,
                StudentCode = "STUOTHER0001",
                CreatedAt = now,
                UpdatedAt = now
            };
            db.Users.Add(other);
            await db.SaveChangesAsync();

            otherToken = jwt.CreateAccessToken(other);
        }

        // other student tries read чужую сессию
        SetBearer(client, otherToken);
        var resp = await client.GetAsync($"/api/my/sessions/{created.Id}");

        resp.StatusCode.Should().NotBe(HttpStatusCode.OK);
        resp.StatusCode.Should().BeOneOf(HttpStatusCode.NotFound, HttpStatusCode.Forbidden, HttpStatusCode.Unauthorized);
    }

    [Trait("Critical", "true")]
    [Fact]
    public async Task Teacher_CannotCompleteOtherTeachersSession()
    {
        var client = _factory.CreateClient();
        var seed = await SeedAsync(client);

        // teacher1 creates session
        SetBearer(client, seed.TeacherToken);
        var created = await CreateSessionAsync(client, seed, "ownership");

        // create other teacher + token
        string otherTeacherToken;
        using (var scope = _factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var jwt = scope.ServiceProvider.GetRequiredService<IJwtTokenService>();
            var hash = scope.ServiceProvider.GetRequiredService<IPasswordHasher>();

            var now = DateTime.UtcNow;
            var other = new UserEntity
            {
                Id = Guid.NewGuid(),
                Email = "other.teacher@local",
                Name = "Other Teacher",
                PasswordHash = hash.Hash("DevPassword123!"),
                Role = UserRole.Teacher,
                CreatedAt = now,
                UpdatedAt = now
            };
            db.Users.Add(other);
            await db.SaveChangesAsync();

            otherTeacherToken = jwt.CreateAccessToken(other);
        }

        // other teacher tries complete чужую сессию
        SetBearer(client, otherTeacherToken);
        var resp = await client.PostAsync($"/api/sessions/{created.Id}/complete", null);

        resp.StatusCode.Should().NotBe(HttpStatusCode.OK);
        resp.StatusCode.Should().NotBe(HttpStatusCode.NoContent);

        resp.StatusCode.Should().BeOneOf(HttpStatusCode.NotFound, HttpStatusCode.Forbidden, HttpStatusCode.Unauthorized);
    }
}
