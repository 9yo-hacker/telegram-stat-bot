using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Application.Auth;
using TutorPlatform.Api.Common.Auth;
using TutorPlatform.Api.Common.Errors;
using TutorPlatform.Api.Contracts.Auth;
using TutorPlatform.Api.Data;
using Microsoft.AspNetCore.RateLimiting;

namespace TutorPlatform.Api.Controllers;

[ApiController]
[Route("api/auth")]
public sealed class AuthController : ControllerBase
{
    private readonly AuthService _auth;
    private readonly AppDbContext _db;

    public AuthController(AuthService auth, AppDbContext db)
    {
        _auth = auth;
        _db = db;
    }

    [EnableRateLimiting("auth_register_ip")]
    [HttpPost("register")]
    [ProducesResponseType(typeof(AuthResponse), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiError), StatusCodes.Status409Conflict)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)] // ProblemDetails автоматически
    public async Task<IActionResult> Register([FromBody] RegisterRequest request, CancellationToken ct)
    {
        try
        {
            var response = await _auth.Register(request, ct);

            // сейчас без Location можно оставить Ok(response)
            return Created(string.Empty, response); // 201
        }
        catch (EmailAlreadyExistsException ex)
        {
            return Conflict(new ApiError("email_already_exists", ex.Message)); // 409
        }
    }

    [EnableRateLimiting("auth_login_ip")]
    [HttpPost("login")]
    [ProducesResponseType(typeof(AuthResponse), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiError), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)] // ProblemDetails автоматически
    public async Task<IActionResult> Login([FromBody] LoginRequest request, CancellationToken ct)
    {
        try
        {
            var response = await _auth.Login(request, ct);
            return Ok(response); // 200
        }
        catch (InvalidCredentialsException)
        {
            return Unauthorized(new ApiError("invalid_credentials"));
        }
    }
    
    [Authorize]
    [HttpGet("me")]
    public async Task<ActionResult<UserProfileDto>> Me(CancellationToken ct)
    {
        var userId = User.GetUserId();

        var user = await _db.Users.SingleAsync(x => x.Id == userId, ct);

        return Ok(AuthMapper.MapProfile(user));
    }
}