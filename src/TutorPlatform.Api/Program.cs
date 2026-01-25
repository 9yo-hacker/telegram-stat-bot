using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddDbContext<AppDbContext>(opt =>
    opt.UseNpgsql(builder.Configuration.GetConnectionString("Default")));

var app = builder.Build();

app.MapControllers();

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.Run();
