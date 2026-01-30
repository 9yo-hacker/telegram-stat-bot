using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Contracts.Courses;

public record CreateCourseRequest(
    // определить минимум как 4 символа а максимум 150
    string Title,
    //минимум не устанавливать, а если поле обязательное то 4, максимум определить как 1000 символов
    string Description,
    //минимум не устанавливать,  а если поле обязательное то 4, максимум определить 2048 символов (нет стандарта который длину ограничивает)
    string? DefaultVideoLink,
    // фиксированный перечень, ограничения не требуются
    CourseStatus? Status
);