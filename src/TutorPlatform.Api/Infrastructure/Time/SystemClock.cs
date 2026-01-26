using TutorPlatform.Api.Application.Abstractions;

namespace TutorPlatform.Api.Infrastructure.Time;

public sealed class SystemClock : IClock
{
    public DateTimeOffset UtcNow => DateTimeOffset.UtcNow;
}
