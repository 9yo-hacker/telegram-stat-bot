using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;
using TutorPlatform.Api.Common.Errors;
using TutorPlatform.Api.Contracts.Lessons;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api")]
[Authorize(Roles = "Teacher")]
public sealed class LessonsController : ControllerBase
{
    private readonly ILessonService _lessons;

    public LessonsController(ILessonService lessons)
    {
        _lessons = lessons;
    }

    // GET /api/courses/{courseId}/lessons
    [HttpGet("courses/{courseId:guid}/lessons")]
    [ProducesResponseType(typeof(IReadOnlyList<LessonResponse>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<LessonResponse>>> GetList(
        Guid courseId,
        CancellationToken ct)
    {
        var teacherId = GetUserId();

        // Важно: сервис может вернуть пустой список, если курс не твой/не найден.
        // Но для удобства UX лучше 404 — поэтому можно изменить сервис на "throw NotFound"
        // или сделать отдельную проверку. Пока оставим как есть:
        var list = await _lessons.GetListAsync(teacherId, courseId, ct);
        return Ok(list);
    }

    // GET /api/lessons/{lessonId}
    [HttpGet("lessons/{lessonId:guid}")]
    [ProducesResponseType(typeof(LessonResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<LessonResponse>> Get(
        Guid lessonId,
        CancellationToken ct)
    {
        var teacherId = GetUserId();

        var lesson = await _lessons.GetAsync(teacherId, lessonId, ct);
        if (lesson is null) return NotFound();

        return Ok(lesson);
    }

    // POST /api/courses/{courseId}/lessons
    [HttpPost("courses/{courseId:guid}/lessons")]
    [ProducesResponseType(typeof(object), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Create(
        Guid courseId,
        [FromBody] CreateLessonRequest req,
        CancellationToken ct)
    {
        var teacherId = GetUserId();

        try
        {
            var lessonId = await _lessons.CreateAsync(teacherId, courseId, req, ct);

            // Можно вернуть только id, чтобы не делать лишний SELECT
            return Created($"/api/lessons/{lessonId}", new { id = lessonId });
        }
        catch (DomainException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
        catch (ArgumentException)
        {
            // если сервис кидает "Course not found"
            return NotFound();
        }
    }

    // PUT /api/lessons/{lessonId}  (у нас patch-like поведение)
    [HttpPut("lessons/{lessonId:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Update(
        Guid lessonId,
        [FromBody] UpdateLessonRequest req,
        CancellationToken ct)
    {
        var teacherId = GetUserId();

        try
        {
            var updated = await _lessons.UpdateAsync(teacherId, lessonId, req, ct);
            if (!updated) return NotFound();

            return NoContent();
        }
        catch (DomainException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    // DELETE /api/lessons/{lessonId}  (архивируем)
    [HttpDelete("lessons/{lessonId:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Archive(
        Guid lessonId,
        CancellationToken ct)
    {
        var teacherId = GetUserId();

        var req = new UpdateLessonRequest(
            Title: null,
            MaterialUrl: null,
            Status: LessonStatus.Archived
        );

        var updated = await _lessons.UpdateAsync(teacherId, lessonId, req, ct);
        if (!updated) return NotFound();

        return NoContent();
    }

    private Guid GetUserId()
    {
        var raw = User.FindFirstValue(ClaimTypes.NameIdentifier)
                  ?? User.FindFirstValue("sub");

        return Guid.Parse(raw!);
    }
}
