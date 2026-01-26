using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Courses;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/courses")]
[Authorize(Roles = "Teacher")]
public class CoursesController : ControllerBase
{
    private readonly ICourseService _courses;

    public CoursesController(ICourseService courses) => _courses = courses;

    [HttpGet]
    public async Task<ActionResult<List<CourseListItemResponse>>> GetMy(CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var items = await _courses.GetMyCoursesAsync(teacherId, ct);
        return Ok(items);
    }

    [HttpGet("{courseId:guid}")]
    public async Task<ActionResult<CourseResponse>> GetById(Guid courseId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var course = await _courses.GetMyCourseAsync(teacherId, courseId, ct);
        if (course is null) return NotFound();
        return Ok(course);
    }

    [HttpPost]
    public async Task<ActionResult<CourseResponse>> Create([FromBody] CreateCourseRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var created = await _courses.CreateAsync(teacherId, req, ct);
        return CreatedAtAction(nameof(GetById), new { courseId = created.Id }, created);
    }

    [HttpPut("{courseId:guid}")]
    public async Task<IActionResult> Update(Guid courseId, [FromBody] UpdateCourseRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var ok = await _courses.UpdateAsync(teacherId, courseId, req, ct);
        if (!ok) return NotFound();
        return NoContent();
    }

    [HttpDelete("{courseId:guid}")]
    public async Task<IActionResult> Archive(Guid courseId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var ok = await _courses.ArchiveAsync(teacherId, courseId, ct);
        if (!ok) return NotFound();
        return NoContent();
    }
}
