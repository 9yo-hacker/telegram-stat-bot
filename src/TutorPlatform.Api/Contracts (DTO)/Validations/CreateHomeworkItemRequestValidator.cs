using FluentValidation;
using TutorPlatform.Api.Contracts.Homework;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class CreateHomeworkItemRequestValidator : AbstractValidator<CreateHomeworkItemRequest>
{
    public CreateHomeworkItemRequestValidator()
    {
        RuleFor(x => x.Title)
            .NotEmpty()
            .MaximumLength(200)
            .Must(s => !string.IsNullOrWhiteSpace(s));

        RuleFor(x => x.Description)
            .MaximumLength(4000);

        RuleFor(x => x.LinkUrl)
            .MaximumLength(2048)
            .Must(ValidationRules.BeHttpUrl);

        // DueAt можно в прошлом — не запрещаем
    }
}
