using FluentValidation;
using TutorPlatform.Api.Contracts.Courses;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class CreateCourseRequestValidator : AbstractValidator<CreateCourseRequest>
{
    public CreateCourseRequestValidator()
    {
        RuleFor(x => x.Title)
            .NotEmpty()
            .MaximumLength(200)
            .Must(s => !string.IsNullOrWhiteSpace(s));

        RuleFor(x => x.Description)
            .NotNull()
            .MaximumLength(4000)
            .Must(s => !string.IsNullOrWhiteSpace(s));

        RuleFor(x => x.DefaultVideoLink)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl);
    }
}
