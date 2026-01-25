# Database Rules (PostgreSQL)

This document defines what must be enforced by DB constraints/indexes
and what must be enforced in application code.

------------------------------------------------------------

## Must enforce in DB (constraints/indexes)

### users
- PK: (id)
- UNIQUE: (email)
- Partial UNIQUE: (student_code) WHERE student_code IS NOT NULL

### courses
- PK: (id)
- FK: teacher_id -> users(id)

### lessons
- PK: (id)
- FK: course_id -> courses(id)
- Index: (course_id)

### enrollments
- PK: (id)
- FK: course_id -> courses(id)
- FK: student_id -> users(id)
- UNIQUE: (course_id, student_id)
- Index: (course_id), (student_id)

### sessions
- PK: (id)
- FK: course_id -> courses(id)
- FK: teacher_id -> users(id)
- FK: student_id -> users(id)
- FK: lesson_id -> lessons(id) NULLABLE
- Index: (teacher_id, starts_at)
- Index: (student_id, starts_at)
- Index: (course_id)

### homework_items
- PK: (id)
- FK: enrollment_id -> enrollments(id)
- FK: created_by_teacher_id -> users(id)
- Index: (enrollment_id, status)
- Optional index: (due_at)

------------------------------------------------------------

## Enforce in application code (business validation)

These cannot be expressed safely with plain FK/UNIQUE constraints.

### Role constraints
- Enrollment.student_id must refer to User with Role=Student
- Session.student_id must refer to User with Role=Student
- Only Teacher can create courses/lessons/enrollments/sessions/homework

### Ownership constraints
- Only Course.Teacher can create/update/revoke enrollments
- Only Session.Teacher can reschedule/cancel/complete session
- Homework.createdByTeacherId must equal Course.TeacherId

### Cross-table invariants
- Session.teacher_id == Course.teacher_id
- If session.lesson_id is not null:
  - Lesson.course_id == Session.course_id
- Session can be created only if there is an Active enrollment for (course_id, student_id)
- If Enrollment is Revoked: block creating NEW sessions (existing sessions stay)
- If Enrollment is Revoked: block creating NEW homework (existing homework stays)

### Snapshot rules
- On session complete:
  - store lesson_title_snapshot + lesson_material_url_snapshot
  - after completion, student sees snapshot, not live content

### No overlap rule
- No validation of overlaps in MVP (explicitly allowed)

------------------------------------------------------------

## Notes on implementation
- Prefer enforcing business rules in a domain/service layer (not controllers).
- Consider adding a few DB triggers only if you later need hard guarantees; MVP can live with app-level validation.
