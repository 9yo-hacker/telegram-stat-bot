# Roadmap

## MVP Scope
Core functionality required to validate the product.

- Authentication (Teacher / Student)
- Courses (teacher-owned)
- Lessons (teacher library; materials via links)
- Enrollment (StudentCode + Plan/Progress)
- Sessions (planned/done/canceled + snapshot)
- Homework items (teacher-managed, per enrollment)

Out of scope for MVP:
- Notifications
- Course player / lesson access control for students (LessonAccess)
- Asset library (uploads)
- Admin UI
- Payments

---------------------------------------------------------

## Stage 1. MVP Implementation

### Scope
- User registration and authentication (Teacher / Student)
- Course CRUD (teacher)
- Lesson CRUD (teacher, MaterialUrl)
- Student enrollment by teacher (StudentCode) + Plan/Progress
- Session scheduling:
  - create/reschedule/cancel
  - mark Done -> store snapshot (Title + MaterialUrl)
  - student visibility only via sessions (planned/live, done/snapshot)
- Homework items per enrollment (create/update/status/deadlines)

### Goal
Deliver a working product that can be used by a tutor and a student in real scenarios.

---------------------------------------------------------

## Stage 2. Testing and Feedback Collection

### Scope
- Internal testing of MVP
- Onboarding first real users
- Collecting feedback from teachers
- Identifying pain points and issues

### Goal
Validate that the product solves a real problem for tutors and students.

---------------------------------------------------------

## Stage 3. UX and Stability Improvements

### Scope
- Improving user flows
- Enhancing usability (especially tablet/iPad usage)
- Fixing critical issues
- Improving overall stability

### Goal
Make the product comfortable for regular usage.

---------------------------------------------------------

## Stage 4. Feature Expansion (Post-MVP)

### Scope
- Course player for students
- Lesson access modes (Course.AccessMode) + LessonAccess (grant/revoke)
- Extended materials management:
  - Content editor (ContentJson)
  - optional file uploads / asset library
- Resource links and assessments (Phase 2 entities)
- Notifications (Telegram and others)
- Administrative functionality

### Goal
Prepare the product for monetization.

---------------------------------------------------------

## Stage 5. Monetization

### Scope
- Subscription model for teachers
- Limits based on pricing plans
- Basic usage analytics

### Goal
Validate economic viability of the product.

---------------------------------------------------------

## Stage 6. Scaling (Post-validation)

### Scope
- Architecture optimization
- Possible service separation
- Infrastructure preparation for growth

### Goal
Scale the product after confirming its value.
