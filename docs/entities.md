# Entities (MVP)

## User
Represents a platform user.

### Roles
- Teacher
- Student
- Admin (post-MVP, no UI)

### Fields
- Id (GUID, PK)
- Email (string, unique)
- PasswordHash (string)
- Role (enum)
- Name (string)
- StudentCode (string, nullable, unique, only for Student)
- IsActive (bool)
- CreatedAt (datetime, UTC)

### Relations
- Teacher → Courses (1:N)
- Teacher → Sessions (1:N)
- Student → Enrollments (1:N)
- Student → Sessions (1:N)

### Rules
- StudentCode is generated when a Student user is created;
  Format: 8-10 digits, generated only for Role=Student;
  StudentCode is unique (DB unique index; nullable allowed);
  Implement as partial unique index where StudentCode IS NOT NULL (PostgreSQL).

--------------------------------------------------

## Course
A course created by a teacher, containing lessons.

### Fields
- Id (GUID, PK)
- TeacherId (GUID, FK → User)
- Title (string)
- Description (string)
- DefaultVideoLink (string, nullable)
- AccessMode (enum, post-MVP): BySessions | Manual | FullAccess
- Status (enum: Draft | Published | Archived)
- CreatedAt (datetime, UTC)

### Relations
- Course → Lessons (1:N)
- Course → Enrollments (1:N)
- Course → Sessions (1:N)

--------------------------------------------------

## Lesson
Educational content inside a course.

### Fields
- Id (GUID, PK)
- CourseId (GUID, FK → Course)
- Title (string)
- MaterialUrl (string, nullable) — MVP: link to material (pdf, doc, site, etc.)
- ContentJson (jsonb, nullable) — post-MVP: blocks editor (text | link | image | file)
- Status (enum: Draft | Published | Archived)
- CreatedAt (datetime, UTC)
- UpdatedAt (datetime, UTC)
- PublishedAt (datetime, nullable)

### Relations
- Lesson → Sessions (1:N)

### Rules
- MVP: snapshot MaterialUrl + Title in Session
- In MVP, lesson Status does not affect student visibility directly;
  student sees lesson only via Sessions.

--------------------------------------------------

## Enrollment
Represents teacher permission to schedule sessions for a student within a course.
In MVP, enrollment does not expose course lessons to the student by itself.

### Fields
- Id (GUID, PK)
- CourseId (GUID, FK → Course)
- StudentId (GUID, FK → User)
- Plan (string, nullable) - plan/programm/goals for student by course.
- Progress (string, nullable) - short progress with student.
- Status (enum: Active | Revoked)
- CreatedAt (datetime, UTC)
- UpdatedAt (datetime, UTC)

### Constraints
- Unique (CourseId, StudentId)

### Rules
- StudentId must refer to a User with Role=Student.
- Active enrollment allows creating new sessions for (CourseId, StudentId).
- Revoked enrollment blocks creating new sessions, 
  but existing sessions remain visible in history.
- Homework items can be created only for Active enrollment.
- Only the Course.Teacher can create/update/revoke enrollments.
- Existing homework items remain visible after enrollment is revoked.

--------------------------------------------------

## LessonAccess(post-MVP):
Access control for lesson: Access may be revoked if lesson not finished

### Fields
- Id (GUID, PK)
- LessonId (GUID, FK → Lesson)
- EnrollmentId (GUID, FK → Enrollment)
- IsActive (bool)
- GrantedAt (datetime)

### Rules

- User.Role must be Student
- LessonAccess can exist only if Student has Enrollment in Lesson.CourseId
- Access may be revoked only if there is no Done session for this enrollment+lesson.

--------------------------------------------------

## HomeworkItem (MVP)
Homework tasks for a student within a course (enrollment)

### Fields

- Id (GUID, PK)
- EnrollmentId (GUID, FK → Enrollment)
- CreatedByTeacherId (GUID, FK → User)
- Title (string)
- Description (string, nullable)
- LinkUrl (string, nullable) — link to materials as doc/exersices
- Status (enum: Todo | Done | Skipped)
- DueAt (datetime, nullable, UTC)
- CreatedAt (datetime, UTC)
- CompletedAt (datetime, nullable, UTC)

### Relations

- Enrollment → HomeworkItems (1:N)

### Index/Constraints

- Index (EnrollmentId, Status)
- (optional) Index (DueAt)

### Rules

- CreatedByTeacherId must equal Course.TeacherId.

--------------------------------------------------

## ResourceLink: Phase 2 (post-MVP)
Saved links/materials for a student within a course.

## Fields

- Id (GUID, PK)
- EnrollmentId (GUID, FK → Enrollment)
- Title (string)
- Url (string)
- Type (enum: Material | Tool | Homework | Other) — can be string, but enum simpler
- Tags (string, nullable) — MVP: string as "grammar, video" (post-MVP may be normalized)
- CreatedAt (datetime, UTC)

## Relations

- Enrollment → ResourceLinks (1:N)

--------------------------------------------------

## Assessment: Phase 2 (post-MVP)
Results and evaluations within an enrollment.

### Fields
- Id (GUID, PK)
- EnrollmentId (GUID, FK → Enrollment)
- Title (string) — "Пробник 1", "Тест по временам"
- Score (decimal/int, nullable) — как решите
- MaxScore (decimal/int, nullable)
- Notes (string, nullable)
- TakenAt (datetime, nullable, UTC)
- CreatedAt (datetime, UTC)

### Relations

- Enrollment → Assessments (1:N)

--------------------------------------------------

## Session
A scheduled lesson between a teacher and a student.

### Fields
- Id (GUID, PK)
- CourseId (GUID, FK → Course)
- TeacherId (GUID, FK → User)
- StudentId (GUID, FK → User)
- LessonId (GUID, FK → Lesson, nullable)
- StartsAt (datetime, UTC)
- DurationMinutes (int)
- Notes (string, nullable)
- Homework (post-MVP: string/url, nullable)
- VideoLink (string, nullable)
- Status (enum: Planned | Done | Canceled)
- LessonMaterialUrlSnapshot (MVP: string, nullable)
- LessonSnapshotJson (post-MVP: jsonb, nullable)
- LessonTitleSnapshot (string, nullable)
- CreatedAt (datetime, UTC)
- UpdatedAt (datetime, UTC)

### Relations
- Session → Teacher
- Session → Student
- Session → Course
- Session → Lesson (optional)

### Rules
- Session is considered completed when tutor marks session as Done.
- For Planned sessions:
  student sees the current (live) version of the attached lesson
  (if LessonId is set).
- After session completion, student sees lesson snapshot stored in session.
- Session.TeacherId == Course.TeacherId
- If Session.VideoLink is null, use Course.DefaultVideoLink
- A session can be created only if there is an Active enrollment
  for (CourseId, StudentId).
- If LessonId is set, then Lesson.CourseId == Session.CourseId
- Student gets video link only via their session (no course-wide link exposure in MVP).
- Only the session's teacher can change status/reschedule/cancel/complete.