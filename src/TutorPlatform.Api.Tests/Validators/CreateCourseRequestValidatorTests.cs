using FluentValidation.Results;
using TutorPlatform.Api.Contracts.Courses;
using TutorPlatform.Api.Contracts.Validation;
using Xunit;

namespace TutorPlatform.Api.Tests.Validators;

public class CreateCourseRequestValidatorTests
{
    private readonly CreateCourseRequestValidator _v = new();

    [Fact]
    public void Title_Empty_ShouldFail()
    {
        var req = new CreateCourseRequest(Title: "", Description: "desc", DefaultVideoLink: null, Status: null);

        var res = _v.Validate(req);

        AssertHasError(res, "Title");
    }

    [Fact]
    public void Title_Whitespace_ShouldFail()
    {
        var req = new CreateCourseRequest(Title: "   ", Description: "desc", DefaultVideoLink: null, Status: null);

        var res = _v.Validate(req);

        AssertHasError(res, "Title");
    }

    [Fact]
    public void DefaultVideoLink_NotHttp_ShouldFail()
    {
        var req = new CreateCourseRequest(Title: "ok", Description: "desc", DefaultVideoLink: "ftp://bad", Status: null);

        var res = _v.Validate(req);

        AssertHasError(res, "DefaultVideoLink");
    }

    [Fact]
    public void Valid_Request_ShouldPass()
    {
        var req = new CreateCourseRequest(
            Title: "Course",
            Description: "desc",
            DefaultVideoLink: "https://meet.example/x",
            Status: null
        );

        var res = _v.Validate(req);

        Assert.True(res.IsValid);
        Assert.Empty(res.Errors);
    }

    private static void AssertHasError(ValidationResult res, string propertyName)
    {
        Assert.False(res.IsValid);
        Assert.Contains(res.Errors, e => e.PropertyName == propertyName);
    }
}
