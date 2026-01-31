using FluentValidation;
using TutorPlatform.Api.Contracts.Sessions;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class CreateSessionRequestValidator : AbstractValidator<CreateSessionRequest>
{
    public CreateSessionRequestValidator()
    {
        RuleFor(x => x.CourseId).NotEmpty();
        RuleFor(x => x.StudentId).NotEmpty();

        // StartsAt может быть в прошлом 

        RuleFor(x => x.DurationMinutes)
            .InclusiveBetween(1, 1440);

        RuleFor(x => x.VideoLink)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl);

        RuleFor(x => x.Notes)
            .MaximumLength(4000);
    }
}
