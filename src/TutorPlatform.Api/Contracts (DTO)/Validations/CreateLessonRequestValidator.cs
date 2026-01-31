using FluentValidation;
using TutorPlatform.Api.Contracts.Lessons;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class CreateLessonRequestValidator : AbstractValidator<CreateLessonRequest>
{
    public CreateLessonRequestValidator()
    {
        RuleFor(x => x.Title)
            .NotEmpty()
            .MaximumLength(200)
            .Must(s => !string.IsNullOrWhiteSpace(s));

        RuleFor(x => x.MaterialUrl)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl);
    }
}
