using FluentValidation;
using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class UpdateHomeworkItemRequestValidator : AbstractValidator<UpdateHomeworkItemRequest>
{
    public UpdateHomeworkItemRequestValidator()
    {
        RuleFor(x => x.Title)
            .MaximumLength(200)
            .Must(ValidationRules.NotBlank)
            .When(x => x.Title is not null);

        RuleFor(x => x.Description)
            .MaximumLength(4000)
            .When(x => x.Description is not null);

        RuleFor(x => x.LinkUrl)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl)
            .When(x => x.LinkUrl is not null);
    }
}
