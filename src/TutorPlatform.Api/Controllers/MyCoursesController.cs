using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Courses;
using TutorPlatform.Api.Contracts.Lessons;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/my/courses")]
[Authorize(Roles = "Student")]
public sealed class MyCoursesController : ControllerBase
{
    private readonly ICourseService _courses;
    private readonly ILessonService _lessons;

    public MyCoursesController(ICourseService courses, ILessonService lessons)
    {
        _courses = courses;
        _lessons = lessons;
    }

    // Left menu: "My courses"
    [HttpGet]
    public async Task<ActionResult<List<CourseListItemResponse>>> GetMy(CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var items = await _courses.GetMyCoursesAsStudentAsync(studentId, ct);
        return Ok(items);
    }

    // Click course -> course details (no management)
    [HttpGet("{courseId:guid}")]
    public async Task<ActionResult<CourseResponse>> GetById(Guid courseId, CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var course = await _courses.GetMyCourseAsStudentAsync(studentId, courseId, ct);
        if (course is null) return NotFound();
        return Ok(course);
    }

    // Course screen: list of lessons with filter Planned/Done (based on sessions for this student)
    [HttpGet("{courseId:guid}/lessons")]
    public async Task<ActionResult<IReadOnlyList<MyLessonListItemResponse>>> GetLessons(
        Guid courseId,
        [FromQuery] string? filter,
        CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var list = await _lessons.GetMyLessonsByCourseAsync(studentId, courseId, filter, ct);
        if (list is null) return NotFound();
        return Ok(list);
    }
}
