using FluentValidation;
using TutorPlatform.Api.Contracts.Enrollments;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class UpdateEnrollmentRequestValidator : AbstractValidator<UpdateEnrollmentRequest>
{
    public UpdateEnrollmentRequestValidator()
    {
        RuleFor(x => x.Plan)
            .MaximumLength(4000)
            .When(x => x.Plan is not null);

        RuleFor(x => x.Progress)
            .MaximumLength(4000)
            .When(x => x.Progress is not null);

        RuleFor(x => x.Plan)
            .Must(ValidationRules.NotBlank)
            .When(x => x.Plan is not null);

        RuleFor(x => x.Progress)
            .Must(ValidationRules.NotBlank)
            .When(x => x.Progress is not null);
    }
}
