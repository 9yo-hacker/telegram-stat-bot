# Product Requirements (MVP)

## 1. Product Goal
Provide a single platform where tutors can manage students, courses, lessons (as a teacher-side library), and scheduled sessions.
Students access learning materials and history only through their sessions (planned/live, done/snapshot).
Homework management is included in MVP (teacher-managed).

## 2. Target Audience
- Private tutors (Teacher)
- Their students (Student)

---------------------------------------------------------------

## 3. Functional Requirements

### 3.1 New User
- A new user can register on the platform.
- During registration, the user selects a role: Teacher or Student.
- Admin role is not available in MVP.

---------------------------------------------------------------

### 3.2 Teacher (MVP)

- A teacher can create, edit, and archive courses.
- A teacher can create, edit, and archive lessons within their courses.
- Lesson status/publication does not control student visibility in MVP; students see lesson materials only via sessions.
- A teacher can add a student to a course using the student identifier (StudentCode), creating an enrollment.
- A teacher can view and update enrollment details (Plan, Progress) and revoke an enrollment.
- Revoked enrollment blocks creating new sessions for that student in the course; existing sessions remain visible in history.
- A teacher can create sessions for enrolled students by selecting date/time, duration, and (optionally) a lesson.
- The system does not validate time overlaps between sessions (a student may have sessions scheduled at the same time).
- A teacher can reschedule or cancel a session.
- A teacher can mark a session as Done; after completion the system stores a snapshot of the lesson material (Title + MaterialUrl) in the session.
- A teacher can attach a video meeting link to a session; if not provided, the course default video link is used.
- A teacher can manage homework items for an active enrollment (create/update/status/deadlines).
- Teachers cannot access courses, lessons, enrollments, sessions, or students of other teachers (except students they have enrolled in their own courses).
- Notifications are out of scope for MVP.

---------------------------------------------------------------

### 3.3 Student (MVP)

- A student can sign in and view only their own data.
- A student can view their scheduled sessions (Planned) and session history (Done/Canceled).
- A student can open a Planned session and see:
  - the video meeting link for that session (Session.VideoLink; if null, Course.DefaultVideoLink),
  - the current (live) lesson material attached to the session (Lesson.MaterialUrl), if LessonId is set.
- A student can open a Done session and see the stored lesson snapshot (LessonTitleSnapshot + LessonMaterialUrlSnapshot) captured at completion time.
- A student cannot browse courses or lessons directly in MVP; lesson visibility is only through sessions.
- A student cannot create, modify, reschedule, cancel, or complete sessions.
- Homework items are teacher-managed in MVP; student interaction with homework is out of scope unless explicitly implemented.
- Notifications are out of scope for MVP.

---------------------------------------------------------------

### 3.4 Admin (Post-MVP)
- Admin can manage users, courses, and lessons.
- Admin can view all registered users.

---------------------------------------------------------------

## 4. MVP Scope

Included in MVP:
- User registration and authentication
- Course creation by teacher
- Lesson creation/editing by teacher (teacher library)
- Student enrollment via StudentCode
- Enrollment notes: Plan/Progress
- Session scheduling (planned/done/canceled)
- Lesson material access for students via sessions only (planned/live, done/snapshot)
- Homework items (teacher-managed) per enrollment

Out of scope for MVP:
- Notifications
- Course player / lesson access control for students (LessonAccess)
- File storage / asset library (uploads)
- Admin UI
- Payments and subscriptions

---------------------------------------------------------------

## 5. Success Metrics (KPI)
- Number of active teachers (created at least one course)
- Number of enrolled students
- Number of completed sessions
- Teacher retention (repeat logins)

---------------------------------------------------------------

## 6. Monetization (Post-MVP)
- Subscription model for teachers
- Pricing tiers based on number of students
- Payments are not included in MVP
