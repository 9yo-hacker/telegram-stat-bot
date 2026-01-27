namespace TutorPlatform.Api.Common.Errors;

public sealed class EmailAlreadyExistsException : Exception
{
    public EmailAlreadyExistsException(string email)
        : base($"Email '{email}' is already registered.") { }
}

public sealed class InvalidCredentialsException : Exception { }

public sealed class InvalidRoleException : Exception
{
    public InvalidRoleException(string? role)
        : base($"Role must be Teacher or Student. Got: '{role}'.") { }
}

public class DomainException : Exception
{
    public DomainException(string message) : base(message) { }
}

public sealed class EntityNotFoundException : Exception
{
    public EntityNotFoundException(string entity, Guid id)
        : base($"{entity} with id '{id}' was not found.") { }
}
