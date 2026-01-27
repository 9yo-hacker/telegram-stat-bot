namespace TutorPlatform.Api.Contracts.Dev;

public record DevSeedResponse(
    string TeacherToken,
    string StudentToken,

    Guid TeacherId,
    Guid StudentId,

    Guid CourseId,
    Guid LessonId,
    Guid EnrollmentId
);
