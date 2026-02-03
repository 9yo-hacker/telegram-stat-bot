using Microsoft.AspNetCore.Mvc;
using TutorPlatform.Api.Application.Abstractions;
using TutorPlatform.Api.Common.Errors;
using TutorPlatform.Api.Contracts.Auth;
using Microsoft.AspNetCore.RateLimiting;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/auth/password-reset")]
public sealed class PasswordResetController : ControllerBase
{
    private readonly IPasswordResetService _svc;
    private readonly IWebHostEnvironment _env;

    public PasswordResetController(IPasswordResetService svc, IWebHostEnvironment env)
    {
        _svc = svc;
        _env = env;
    }

    // 1) Request reset
    // всегда 200 OK.
    // Токен отдаём ТОЛЬКО в Development и только при X-Dev-Seed: 1 (фронт уже тестит)
    [EnableRateLimiting("forgot_ip")]
    [HttpPost("request")]
    public async Task<ActionResult<PasswordResetRequestResponse>> RequestReset(
        [FromBody] PasswordResetRequest req,
        [FromHeader(Name = "X-Dev-Seed")] string? devSeed,
        CancellationToken ct)
    {
        var token = await _svc.RequestAsync(req.Email, ct);

        if (_env.IsDevelopment() && devSeed == "1")
            return Ok(new PasswordResetRequestResponse(token));

        return Ok(new PasswordResetRequestResponse(null));
    }

    // 2) Confirm reset (форма "новый пароль")
    [HttpPost("confirm")]
    public async Task<IActionResult> Confirm([FromBody] PasswordResetConfirmRequest req, CancellationToken ct)
    {
        var (ok, err) = await _svc.ConfirmAsync(req.Token, req.NewPassword, ct);
        if (!ok) return BadRequest(new ApiError(err ?? "invalid_or_expired"));

        return NoContent(); // 204
    }
}
