using FluentValidation;
using TutorPlatform.Api.Contracts.Sessions;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class UpdateSessionRequestValidator : AbstractValidator<UpdateSessionRequest>
{
    public UpdateSessionRequestValidator()
    {
        RuleFor(x => x.DurationMinutes)
            .InclusiveBetween(1, 1440)
            .When(x => x.DurationMinutes.HasValue);

        RuleFor(x => x.VideoLink)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl)
            .When(x => x.VideoLink is not null);

        RuleFor(x => x.Notes)
            .MaximumLength(4000)
            .When(x => x.Notes is not null);

        // StartsAt может быть в прошлом
    }
}
