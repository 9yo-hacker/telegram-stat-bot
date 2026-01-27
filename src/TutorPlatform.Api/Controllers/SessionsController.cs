using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Contracts.Sessions;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/sessions")]
[Authorize(Roles = "Teacher")]
public class SessionsController : ControllerBase
{
    private readonly ISessionService _sessions;
    public SessionsController(ISessionService sessions) => _sessions = sessions;

    [HttpGet]
    public async Task<ActionResult<List<SessionResponse>>> Get(
        [FromQuery] Guid? courseId,
        [FromQuery] Guid? studentId,
        [FromQuery] DateTime? from,
        [FromQuery] DateTime? to,
        [FromQuery] int? status,
        CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var list = await _sessions.GetTeacherSessionsAsync(teacherId, courseId, studentId, from, to, status, ct);
        return Ok(list);
    }

    [HttpPost]
    public async Task<ActionResult<SessionResponse>> Create(CreateSessionRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (session, error) = await _sessions.CreateAsync(teacherId, req, ct);

        return error switch
        {
            "course_not_found" => NotFound(),
            "enrollment_not_found" => Conflict(), // QA #20 (можно 404, но конфликт логичнее)
            "revoked" => Conflict(),              // QA #21
            "lesson_wrong_course" => BadRequest(),// QA #22
            _ => CreatedAtAction(nameof(Get), new { }, session!)
        };
    }

    [HttpPut("{sessionId:guid}")]
    public async Task<IActionResult> Update(Guid sessionId, UpdateSessionRequest req, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _sessions.UpdateAsync(teacherId, sessionId, req, ct);

        if (!ok)
        {
            return error switch
            {
                "not_found" => NotFound(),
                "lesson_wrong_course" => BadRequest(),
                "done_via_complete_only" => BadRequest(),
                _ => BadRequest()
            };
        }

        return NoContent(); // 204
    }

    [HttpPost("{sessionId:guid}/complete")]
    public async Task<IActionResult> Complete(Guid sessionId, CancellationToken ct)
    {
        var teacherId = User.GetUserId();
        var (ok, error) = await _sessions.CompleteAsync(teacherId, sessionId, ct);

        if (!ok)
        {
            return error switch
            {
                "not_found" => NotFound(),
                "cannot_complete_canceled" => Conflict(),
                _ => BadRequest()
            };
        }

        return NoContent(); // 204
    }
}
