# QA Checklist (MVP)

## Test accounts
- Teacher A
- Teacher B
- Student S1
- Student S2

------------------------------------------------------------

## Auth

1. Register Teacher -> can login -> token works
2. Register Student -> studentCode generated (8-10 digits) -> can login
3. Login fails with wrong password
4. Email uniqueness enforced

------------------------------------------------------------

## Courses (Teacher)

5. Teacher A creates course -> visible in Teacher A list
6. Teacher B cannot access Teacher A course (404/403)
7. Teacher A updates course fields
8. Teacher A archives course (status=Archived) -> remains in list or filtered (expected behavior defined)

------------------------------------------------------------

## Lessons (Teacher)

9. Teacher A creates lesson in own course with MaterialUrl
10. Teacher B cannot access Teacher A lesson
11. Teacher A updates lesson title/materialUrl
12. Student cannot list lessons directly (no endpoint / forbidden)

------------------------------------------------------------

## Enrollment (Teacher)

13. StudentCode is unique: enrolling by studentCode finds correct student
14. Teacher A enrolls S1 into Course A -> enrollment created
15. Unique (CourseId, StudentId): re-enroll same student into same course -> conflict
16. Teacher B cannot create enrollment in Teacher A course
17. Teacher A updates enrollment Plan/Progress
18. Teacher A revokes enrollment -> status=Revoked

------------------------------------------------------------

## Sessions (Teacher)

19. Teacher A creates session for enrolled S1 -> success
20. Create session without enrollment -> blocked (404/409)
21. Create session when enrollment Revoked -> blocked (409/403)
22. Create session with lesson from another course -> blocked (400/409)
23. Teacher B cannot edit Teacher A session
24. Teacher A reschedules session (startsAt changes)
25. Teacher A cancels session -> status=Canceled
26. No overlap validation:
    - Create two sessions same time for S1 -> allowed
    - Create sessions for S1 by Teacher A and Teacher B same time -> allowed

------------------------------------------------------------

## Session completion + snapshot

27. Planned session with LessonId:
    - Student sees live lesson MaterialUrl
28. Teacher updates Lesson.MaterialUrl after session planned:
    - Student sees updated MaterialUrl (live) for Planned session
29. Teacher completes session (Done):
    - Snapshot saved (LessonTitleSnapshot + LessonMaterialUrlSnapshot)
30. Teacher changes lesson title/materialUrl after completion:
    - Student still sees snapshot in Done session
31. Student cannot complete/cancel/reschedule sessions

------------------------------------------------------------

## Video link behavior

32. Course has DefaultVideoLink, session VideoLink null:
    - student sees effective video link = course default
33. Session has VideoLink set:
    - student sees session video link
34. Student cannot see course-wide video link outside session context

------------------------------------------------------------

## HomeworkItem (Teacher-managed)

35. Teacher A creates homework item for Active enrollment -> success
36. Teacher A updates homework status Todo -> Done -> completedAt set
37. Teacher A sets dueAt, list shows correct ordering (if implemented)
38. Teacher B cannot create homework for Teacher A enrollment
39. Enrollment Revoked:
    - Creating new homework is blocked
    - Existing homework remains visible

------------------------------------------------------------

## Security / access boundaries

40. Student S1 cannot access sessions of S2
41. Student S1 cannot access enrollments directly unless you expose them (if exposed, only own)
42. Teacher A can only see students they enrolled (or via sessions/enrollments)
