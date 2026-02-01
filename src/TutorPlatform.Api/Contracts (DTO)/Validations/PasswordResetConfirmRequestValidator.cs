using FluentValidation;
using TutorPlatform.Api.Contracts.Auth;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class PasswordResetConfirmRequestValidator : AbstractValidator<PasswordResetConfirmRequest>
{
    public PasswordResetConfirmRequestValidator()
    {
        RuleFor(x => x.Token)
            .NotEmpty()
            .MinimumLength(20)
            .MaximumLength(300);

        RuleFor(x => x.NewPassword)
            .NotEmpty()
            .MinimumLength(6)
            .MaximumLength(30);
    }
}
