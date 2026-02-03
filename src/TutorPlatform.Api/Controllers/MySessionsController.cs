using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Sessions;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/my/sessions")]
[Authorize(Roles = "Student")]
public class MySessionsController : ControllerBase
{
    private readonly ISessionService _sessions;
    public MySessionsController(ISessionService sessions) => _sessions = sessions;

    [HttpGet]
    public async Task<ActionResult<List<MySessionListItemResponse>>> GetMy(
        [FromQuery] Guid? courseId,
        [FromQuery] DateTime? from,
        [FromQuery] DateTime? to,
        [FromQuery] int? status,
        CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var list = await _sessions.GetMySessionsAsync(studentId, courseId, from, to, status, ct);
        return Ok(list);
    }

    [HttpGet("{sessionId:guid}")]
    public async Task<ActionResult<MySessionDetailsResponse>> GetMyById(Guid sessionId, CancellationToken ct)
    {
        var studentId = User.GetUserId();
        var item = await _sessions.GetMySessionAsync(studentId, sessionId, ct);
        if (item is null) return NotFound(); // QA #40
        return Ok(item);
    }
}
