using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Enrollments;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api")]
[Authorize(Roles = "Teacher")]
public class EnrollmentsController : ControllerBase
{
    private readonly IEnrollmentService _enrollments;
    public EnrollmentsController(IEnrollmentService enrollments) => _enrollments = enrollments;

    [HttpGet("courses/{courseId:guid}/enrollments")]
    public async Task<ActionResult<List<EnrollmentResponse>>> GetByCourse(Guid courseId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var list = await _enrollments.GetByCourseAsync(teacherId, courseId, ct);

        if (list is null) return NotFound(); // точно вернет 404 (нет доступа / не существует)

        return Ok(list);
    }

    [HttpPost("courses/{courseId:guid}/enrollments")]
    public async Task<ActionResult<EnrollmentResponse>> Create(Guid courseId, CreateEnrollmentRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();

        var (enrollment, error) = await _enrollments.CreateAsync(teacherId, courseId, req.StudentCode, ct);
        if (error == "course_not_found") return NotFound();
        if (error == "student_not_found") return NotFound(); // или 400 — но по QA удобнее 404
        if (error == "already_enrolled") return Conflict();

        return CreatedAtAction(nameof(GetByCourse), new { courseId }, enrollment);
    }

    [HttpPut("enrollments/{enrollmentId:guid}")]
    public async Task<IActionResult> Update(Guid enrollmentId, UpdateEnrollmentRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _enrollments.UpdateAsync(teacherId, enrollmentId, req, ct);

        if (!ok && error == "not_found") return NotFound();
        return NoContent(); // 204
    }

    [HttpPost("enrollments/{enrollmentId:guid}/revoke")]
    public async Task<IActionResult> Revoke(Guid enrollmentId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _enrollments.RevokeAsync(teacherId, enrollmentId, ct);

        if (!ok && error == "not_found") return NotFound();
        return NoContent(); // 204
    }
}
