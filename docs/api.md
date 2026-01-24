# API (MVP)

## Conventions
- Base path: `/api`
- Auth: Bearer JWT
- All times: UTC
- IDs: GUID
- Role-based access: Teacher / Student

## Error format
- 400 BadRequest: validation errors
- 401 Unauthorized: not logged in
- 403 Forbidden: logged in but not allowed
- 404 NotFound: entity not found (or not owned)
- 409 Conflict: business rule conflict (e.g., revoked enrollment)

------------------------------------------------------------

## Auth

### POST /api/auth/register
Create user (Teacher or Student).
- Request: `{ email, password, name, role }`
- Response: `{ token, user }`
Rules:
- If role=Student => generate StudentCode (8-10 digits).
- Email unique.

### POST /api/auth/login
- Request: `{ email, password }`
- Response: `{ token, user }`

### GET /api/auth/me
Returns current user profile.

------------------------------------------------------------

## Courses (Teacher only)

### GET /api/courses
List teacher's courses.

### POST /api/courses
Create course.
- Request: `{ title, description, defaultVideoLink?, status? }`

### GET /api/courses/{courseId}
Get course (teacher-owned).

### PUT /api/courses/{courseId}
Update course fields.

### DELETE /api/courses/{courseId}  (or PATCH status=Archived)
Archive course (recommended: soft archive via Status).

Rules:
- Teacher can access only own courses.

------------------------------------------------------------

## Lessons (Teacher only)

### GET /api/courses/{courseId}/lessons
List lessons for course (teacher-owned).

### POST /api/courses/{courseId}/lessons
Create lesson.
- Request: `{ title, materialUrl?, status? }`

### GET /api/lessons/{lessonId}
Get lesson (teacher-owned via course).

### PUT /api/lessons/{lessonId}
Update lesson.

### DELETE /api/lessons/{lessonId} (or PATCH status=Archived)
Archive lesson.

Rules:
- Lesson visibility for students is NOT based on Status in MVP.
- Student sees lesson only via sessions.

------------------------------------------------------------

## Enrollments (Teacher only)

### GET /api/courses/{courseId}/enrollments
List enrollments of course.

### POST /api/courses/{courseId}/enrollments
Add student to course by StudentCode.
- Request: `{ studentCode }`
- Response: Enrollment

Rules:
- Unique (courseId, studentId).
- Only Course.Teacher can create enrollment.

### PUT /api/enrollments/{enrollmentId}
Update Plan/Progress and/or Status.
- Request: `{ plan?, progress?, status? }`

Rules:
- If status changed to Revoked: new sessions cannot be created.
- Existing sessions remain visible.

------------------------------------------------------------

## Sessions

### Teacher endpoints

#### GET /api/sessions
List teacher sessions (filters recommended):
- `from`, `to`, `status`, `studentId`, `courseId`

#### POST /api/sessions
Create session.
- Request: `{ courseId, studentId, startsAt, durationMinutes, lessonId?, videoLink?, notes? }`

Rules:
- Must have Active enrollment for (courseId, studentId).
- Session.TeacherId must equal Course.TeacherId.
- If lessonId is set => lesson.courseId must equal session.courseId.
- If videoLink null => use course.defaultVideoLink.
- No overlap validation in MVP.

#### PUT /api/sessions/{sessionId}
Reschedule/update:
- `{ startsAt?, durationMinutes?, lessonId?, videoLink?, notes?, status? }`

Rules:
- Only session's teacher can edit.
- Status can be Planned/Canceled (Done only via complete endpoint recommended).

#### POST /api/sessions/{sessionId}/complete
Mark Done and store snapshot.
- Behavior:
  - status => Done
  - if lessonId set => copy Lesson.Title and Lesson.MaterialUrl into snapshot fields

------------------------------------------------------------

### Student endpoints

#### GET /api/my/sessions
List student's sessions (Planned/Done/Canceled).

#### GET /api/my/sessions/{sessionId}
Get session details (student-owned).
Response should include:
- videoLinkEffective = session.videoLink ?? course.defaultVideoLink
- If status=Planned:
  - liveLessonMaterialUrl = lesson.materialUrl (if lessonId set)
- If status=Done:
  - lessonTitleSnapshot + lessonMaterialUrlSnapshot

Rules:
- Student can access only their sessions.
- Student cannot edit/complete/cancel sessions.

------------------------------------------------------------

## Homework (Teacher-managed, MVP)

### GET /api/enrollments/{enrollmentId}/homework
List homework items for enrollment.

### POST /api/enrollments/{enrollmentId}/homework
Create homework item.
- Request: `{ title, description?, linkUrl?, dueAt?, status? }`

Rules:
- Only Course.Teacher can create.
- Enrollment must be Active.
- createdByTeacherId must equal course.teacherId.

### PUT /api/homework/{homeworkId}
Update homework:
- `{ title?, description?, linkUrl?, dueAt?, status? }`

Rules:
- Only Course.Teacher can update.
- If setting status=Done => set completedAt.

### DELETE /api/homework/{homeworkId}
Optional for MVP (can do soft delete later).
