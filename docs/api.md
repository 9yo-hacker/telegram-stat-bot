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

## Success format
- 200 OK: operation made successfully
- 201 Created: entity created
- 204 No content: entity deleted

------------------------------------------------------------

## Auth

### POST /api/auth/register
Create user (Teacher or Student).
- Request: `{ email, password, name, role }`
- Response body: `{ token, user }`
- Response status: 201 Created
Rules:
- If role=Student => generate StudentCode (8-10 digits).
- Email unique.

### POST /api/auth/login
- Request: `{ email, password }`
- Response body: `{ token, user }
- Response status: 200 ОК`

### GET /api/auth/me
Returns current user profile.
Response status: 200 ОК

------------------------------------------------------------

## Courses (Teacher only)

### GET /api/courses
List teacher's courses.
Response status: 200 ОК

### POST /api/courses
Create course.
- Request: `{ title, description, defaultVideoLink?, status? }`
- Response status: 201 Created

### GET /api/courses/{courseId}
Get course (teacher-owned).
Response status: 200 ОК

### PUT /api/courses/{courseId}
Update course fields.
Response status: 200 ОК

### DELETE /api/courses/{courseId}  (or PATCH status=Archived)
Archive course (recommended: soft archive via Status).
Response status: if DELETE 204 No content, if PATCH 200 OK

Rules:
- Teacher can access only own courses.

------------------------------------------------------------

## Lessons (Teacher only)

### GET /api/courses/{courseId}/lessons
List lessons for course (teacher-owned).
Response status: 200 ОК

### POST /api/courses/{courseId}/lessons
Create lesson.
- Request: `{ title, materialUrl?, status? }`
- Response status: 201 Created

### GET /api/lessons/{lessonId}
Get lesson (teacher-owned via course).
Response status: 200 ОК

### PUT /api/lessons/{lessonId}
Update lesson.
Response status: 200 ОК

### DELETE /api/lessons/{lessonId} (or PATCH status=Archived)
Archive lesson.
Response status: if DELETE 204 No Content, if PATCH 200 OK

Rules:
- Lesson visibility for students is NOT based on Status in MVP.
- Student sees lesson only via sessions.

------------------------------------------------------------

## Enrollments (Teacher only)

### GET /api/courses/{courseId}/enrollments
List enrollments of course.
Response status: 200 ОК

### POST /api/courses/{courseId}/enrollments
Add student to course by StudentCode.
- Request: `{ studentCode }`
- Response: Enrollment
- Response status: 201 Created

Rules:
- Unique (courseId, studentId).
- Only Course.Teacher can create enrollment.

### PUT /api/enrollments/{enrollmentId}
Update Plan/Progress and/or Status.
- Request: `{ plan?, progress?, status? }`
- Response status: 200 ОК

Rules:
- If status changed to Revoked: new sessions cannot be created.
- Existing sessions remain visible.

------------------------------------------------------------

## Sessions

### Teacher endpoints

#### GET /api/sessions
List teacher sessions (filters recommended):
- `from`, `to`, `status`, `studentId`, `courseId`
Response status: 200 ОК

#### POST /api/sessions
Create session.
- Request: `{ courseId, studentId, startsAt, durationMinutes, lessonId?, videoLink?, notes? }`
- Response status: 201 Created

Rules:
- Must have Active enrollment for (courseId, studentId).
- Session.TeacherId must equal Course.TeacherId.
- If lessonId is set => lesson.courseId must equal session.courseId.
- If videoLink null => use course.defaultVideoLink.
- No overlap validation in MVP.

#### PUT /api/sessions/{sessionId}
Reschedule/update:
- `{ startsAt?, durationMinutes?, lessonId?, videoLink?, notes?, status? }`
Response status: 200 ОК

Rules:
- Only session's teacher can edit.
- Status can be Planned/Canceled (Done only via complete endpoint recommended).

#### POST /api/sessions/{sessionId}/complete
Mark Done and store snapshot.
- Behavior:
  - status => Done
  - if lessonId set => copy Lesson.Title and Lesson.MaterialUrl into snapshot fields
Response status: 200 ОК

------------------------------------------------------------

### Student endpoints

#### GET /api/my/sessions
List student's sessions (Planned/Done/Canceled).
Response status: 200 ОК

#### GET /api/my/sessions/{sessionId}
Get session details (student-owned).
Response status: 200 ОК

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
Response status: 200 ОК

### POST /api/enrollments/{enrollmentId}/homework
Create homework item.
- Request: `{ title, description?, linkUrl?, dueAt?, status? }`
- Response status: 201 Created

Rules:
- Only Course.Teacher can create.
- Enrollment must be Active.
- createdByTeacherId must equal course.teacherId.

### PUT /api/homework/{homeworkId}
Update homework:
- `{ title?, description?, linkUrl?, dueAt?, status? }`
Response status: 200 ОК

Rules:
- Only Course.Teacher can update.
- If setting status=Done => set completedAt.

### DELETE /api/homework/{homeworkId}
Optional for MVP (can do soft delete later).
Response status: if DELETE 204 No content, otherwise 200 OK
