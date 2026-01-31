using FluentValidation;
using TutorPlatform.Api.Contracts.Enrollments;

namespace TutorPlatform.Api.Contracts.Validation;

public sealed class CreateEnrollmentRequestValidator : AbstractValidator<CreateEnrollmentRequest>
{
    public CreateEnrollmentRequestValidator()
    {
        RuleFor(x => x.StudentCode)
            .NotEmpty()
            .Must(code =>
            {
                code = code.Trim();
                if (code.Length != 9) return false;
                foreach (var ch in code)
                    if (!char.IsDigit(ch)) return false;
                return true;
            })
            .WithMessage("ID ученика должен содержать ровно 9 цифр.");
    }
}
