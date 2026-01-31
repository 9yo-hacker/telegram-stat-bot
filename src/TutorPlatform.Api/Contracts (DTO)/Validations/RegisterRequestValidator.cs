using FluentValidation;
using TutorPlatform.Api.Contracts.Auth;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class RegisterRequestValidator : AbstractValidator<RegisterRequest>
{
    public RegisterRequestValidator()
    {
        RuleFor(x => x.Email)
            .NotEmpty()
            .EmailAddress()
            .MaximumLength(254);

        RuleFor(x => x.Password)
            .NotEmpty()
            .MinimumLength(6)
            .MaximumLength(30);

        RuleFor(x => x.Name)
            .NotEmpty()
            .MinimumLength(2)
            .MaximumLength(30);

        RuleFor(x => x.Role)
            .NotEmpty()
            .Must(r => r is "Teacher" or "Student");
    }
}
