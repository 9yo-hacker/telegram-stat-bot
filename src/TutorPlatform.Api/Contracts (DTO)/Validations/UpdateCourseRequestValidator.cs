using FluentValidation;
using TutorPlatform.Api.Contracts.Courses;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class UpdateCourseRequestValidator : AbstractValidator<UpdateCourseRequest>
{
    public UpdateCourseRequestValidator()
    {
        RuleFor(x => x.Title)
            .MaximumLength(200)
            .Must(ValidationRules.NotBlank)
            .When(x => x.Title is not null);

        RuleFor(x => x.Description)
            .MaximumLength(4000)
            .When(x => x.Description is not null);

        RuleFor(x => x.DefaultVideoLink)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl)
            .When(x => x.DefaultVideoLink is not null);
    }
}
