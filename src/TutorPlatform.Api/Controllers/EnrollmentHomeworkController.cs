using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/enrollments/{enrollmentId:guid}/homework")]
[Authorize(Roles = "Teacher")]
public class EnrollmentHomeworkController : ControllerBase
{
    private readonly IHomeworkService _hw;
    public EnrollmentHomeworkController(IHomeworkService hw) => _hw = hw;

    [HttpGet]
    public async Task<ActionResult<List<HomeworkItemResponse>>> Get(Guid enrollmentId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var list = await _hw.GetByEnrollmentAsync(teacherId, enrollmentId, ct);
        if (list is null) return NotFound();
        return Ok(list);
    }

    [HttpPost]
    public async Task<ActionResult<HomeworkItemResponse>> Create(Guid enrollmentId, CreateHomeworkItemRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (item, error) = await _hw.CreateAsync(teacherId, enrollmentId, req, ct);

        return error switch
        {
            "not_found" => NotFound(),
            "revoked" => Conflict(),
            _ => CreatedAtAction(nameof(Get), new { enrollmentId }, item!)
        };
    }
}
