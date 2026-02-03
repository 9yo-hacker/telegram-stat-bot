using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/homework")]
[Authorize(Roles = "Teacher")]
public class HomeworkController : ControllerBase
{
    private readonly IHomeworkService _hw;
    public HomeworkController(IHomeworkService hw) => _hw = hw;

    [HttpPut("{homeworkId:guid}")]
    public async Task<IActionResult> Update(Guid homeworkId, UpdateHomeworkItemRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _hw.UpdateAsync(teacherId, homeworkId, req, ct);

        if (!ok) return error == "not_found" ? NotFound() : BadRequest();
        return NoContent();
    }

    [HttpDelete("{homeworkId:guid}")]
    public async Task<IActionResult> Delete(Guid homeworkId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _hw.DeleteAsync(teacherId, homeworkId, ct);

        if (!ok) return error == "not_found" ? NotFound() : BadRequest();
        return NoContent();
    }

    // Teacher: mark homework as checked (comment + grade)
    [HttpPost("{homeworkId:guid}/check")]
    public async Task<IActionResult> Check(Guid homeworkId, CheckHomeworkRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _hw.CheckAsync(teacherId, homeworkId, req, ct);

        if (!ok) return error == "not_found" ? NotFound() : BadRequest(new { error });
        return NoContent();
    }
}
