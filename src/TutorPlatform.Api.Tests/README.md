# Тесты покрывают:

## ✅ Sessions (Application/Sessions/SessionService.cs)

### Create_AllowsStartsAtInPast_MvpRule — StartsAt в прошлом разрешён
### Create_Fails_WhenEnrollmentRevoked — при revoked нельзя создавать
### Complete_SetsSnapshot_FromLesson — при /complete пишется snapshot из Lesson
### Complete_IsIdempotent_WhenAlreadyDone — complete идемпотентен
### GetMySession_VideoLinkEffective_UsesSessionOverride_ElseCourseDefault — session.videoLink ?? course.defaultVideoLink
### GetMySession_Planned_ReturnsLiveMaterialUrl_DoneReturnsSnapshotOnly — planned: live materialUrl, done: только snapshot

## ✅ Homework (Application/Homework/HomeworkService.cs)
### Create_Todo_SetsCompletedAtNull
### Create_DoneOrSkipped_SetsCompletedAt
### Update_StatusToTodo_ClearsCompletedAt
### Create_Fails_WhenEnrollmentRevoked

## ✅ Валидатор (пример)
### CreateCourseRequestValidatorTests — быстрые sanity checks для FluentValidation (пустой title, плохой url и т.д.)