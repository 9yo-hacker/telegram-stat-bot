using FluentValidation;
using TutorPlatform.Api.Contracts.Auth;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class PasswordResetRequestValidator : AbstractValidator<PasswordResetRequest>
{
    public PasswordResetRequestValidator()
    {
        RuleFor(x => x.Email)
            .NotEmpty()
            .EmailAddress()
            .MaximumLength(254);
    }
}
