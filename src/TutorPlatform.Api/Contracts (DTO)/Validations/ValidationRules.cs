namespace TutorPlatform.Api.Contracts.Validation;

public static class ValidationRules
{
    public static bool BeHttpUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url)) return true;
        if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) return false;
        return uri.Scheme is "http" or "https";
    }

    public static bool NotBlank(string? s) => s is null || !string.IsNullOrWhiteSpace(s);
}
