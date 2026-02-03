using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/my/homework")]
[Authorize(Roles = "Student")]
public sealed class MyHomeworkController : ControllerBase
{
    private readonly IHomeworkService _hw;
    public MyHomeworkController(IHomeworkService hw) => _hw = hw;

    // Left menu: "Домашки" (list)
    // filter: active / checked
    [HttpGet]
    public async Task<ActionResult<List<MyHomeworkListItemResponse>>> GetMy(
        [FromQuery] string? filter,
        CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var list = await _hw.GetMyAsync(studentId, filter, ct);
        return Ok(list);
    }

    [HttpGet("{homeworkId:guid}")]
    public async Task<ActionResult<MyHomeworkDetailsResponse>> GetById(Guid homeworkId, CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var item = await _hw.GetMyByIdAsync(studentId, homeworkId, ct);
        if (item is null) return NotFound();
        return Ok(item);
    }

    // UI: button "add answer" -> submit
    [HttpPost("{homeworkId:guid}/answer")]
    public async Task<IActionResult> SubmitAnswer(Guid homeworkId, SubmitHomeworkAnswerRequest req, CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var (ok, error) = await _hw.SubmitAnswerAsync(studentId, homeworkId, req, ct);

        if (!ok)
            return error == "not_found" ? NotFound() : BadRequest(new { error });

        return NoContent();
    }
}
