# Architectural and Product Decisions

## Decision 1: Lesson vs Session
Lesson represents learning content (teacher-side library).
Session represents a scheduled meeting with a student.
These concepts are separated to avoid ambiguity.

Status: Accepted

--------------------------------------------------------

## Decision 2: No Session Time Conflict Validation
The system does not validate overlapping sessions for teachers or students in MVP.

Reason: Reduce complexity and allow flexible scheduling.

Status: Accepted

--------------------------------------------------------

## Decision 3: Student Lesson Visibility Model (MVP)
Students do not browse courses/lessons directly in MVP.
Students access lesson materials only via their sessions:
- Planned session: student sees the current (live) lesson material (if LessonId is set).
- Done session: student sees the lesson snapshot stored in the session.

Reason: Prevent content leakage and keep MVP simple while preserving history.

Status: Accepted

--------------------------------------------------------

## Decision 4: Lesson Content Snapshot
Lesson material is captured at session level for completed sessions (Done).
Full lesson versioning is postponed.

Reason: Simpler MVP implementation and stable session history.

Status: Accepted

--------------------------------------------------------

## Decision 5: No Notifications in MVP
Telegram and other notifications are excluded from MVP.

Reason: Focus on core learning workflows.

Status: Accepted

--------------------------------------------------------

## Decision 6: No Admin UI in MVP
Admin functionality will be implemented after MVP validation.

Reason: Admin workflows do not affect MVP validation.

Status: Accepted

--------------------------------------------------------

## Decision 7: Lesson access control (post-MVP)
- Student lesson access can be stored in a separate table LessonAccess.
- Teacher manages access (grant / revoke).
- If there is a completed Session (status = Done) for enrollment+lesson,
  access is considered fixed and cannot be revoked.
- Enrollment allows scheduling sessions and keeping per-student workspace in a course;
  it does not expose lessons to students automatically in MVP.
