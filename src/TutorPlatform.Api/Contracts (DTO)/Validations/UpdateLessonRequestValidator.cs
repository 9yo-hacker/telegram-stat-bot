using FluentValidation;
using TutorPlatform.Api.Contracts.Lessons;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class UpdateLessonRequestValidator : AbstractValidator<UpdateLessonRequest>
{
    public UpdateLessonRequestValidator()
    {
        RuleFor(x => x.Title)
            .MaximumLength(200)
            .Must(ValidationRules.NotBlank)
            .When(x => x.Title is not null);

        RuleFor(x => x.MaterialUrl)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl)
            .When(x => x.MaterialUrl is not null);
    }
}
