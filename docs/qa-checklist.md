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
6. Teacher B cannot access Teacher A course -> 404 - suggestion to use 404 to not show if it is even exists
7. Teacher A updates his course fields
8. Teacher A/B updates not exist course -> 404
9. Teacher A tries to update course of teacher B -> 404 
10. Teacher A archives course (status=Archived) -> remains in list or filtered (expected behavior defined)
11. Teacher A tries update his archived course -> 200 OK

------------------------------------------------------------

## Lessons (Teacher)

12. Teacher A creates lesson in own course with MaterialUrl 
13. Teacher B cannot access Teacher A lesson 
14. Teacher A updates lesson title/materialUrl 
15. Teacher A/B updates not exist lesson -> 404 
16. Teacher A tries to update lesson of teacher B -> 404 
17. Teacher A archives lesson (status=Archived) -> remains in list or filtered (expected behavior defined)
18. Student cannot list lessons directly (no endpoint / forbidden)
19. Teacher A tries update his archived lesson -> 200/400 ? (надо определить)

------------------------------------------------------------

## Enrollment (Teacher)

20. StudentCode is unique: enrolling by studentCode finds correct student 
21. Teacher cant create enroll for not exist student 
22. Teacher A enrolls S1 into Course A -> enrollment created, student don't see the lessons of course until Session created 
23. Unique (CourseId, StudentId): re-enroll same student into same course -> 409 conflict 
24. Teacher A can unenroll S1 and enroll S2 in the same course — 200 ok 
25. Teacher B cannot create enrollment in Teacher A course 
26. Teacher A updates enrollment Plan/Progress 
27. Teacher A revokes enrollment -> status=Revoked
28. Teacher A revokes enrollment for student with active session in future -> 200 ok

------------------------------------------------------------

## Sessions (Teacher)

29. Teacher A creates session for enrolled S1 -> success 
30. Teacher A creates session with startsAt time in the past -> 400 or not allowed on front 
31. Create session without enrollment -> blocked (404/409)
32. Create session when enrollment Revoked -> blocked (409/403)
33. Create session with lesson from another course -> blocked (400/409)
34. Teacher B cannot edit Teacher A session 
35. Teacher A reschedules session (startsAt changes)
36. Teacher A cancels session -> status=Canceled 
37. Teacher tries to create session for archived lesson -> 400 
38. No overlap validation:
    - Create two sessions same time for S1 -> allowed
    - Create sessions for S1 by Teacher A and Teacher B same time -> allowed

------------------------------------------------------------

## Session completion + snapshot

39. Planned session with LessonId:
    - Student sees live lesson MaterialUrl
40. Teacher updates Lesson.MaterialUrl after session planned:
    - Student sees updated MaterialUrl (live) for Planned session
41. Teacher completes session (Done):
    - Snapshot saved (LessonTitleSnapshot + LessonMaterialUrlSnapshot)
42. Teacher changes lesson title/materialUrl after completion:
    - Student still sees snapshot in Done session
43. Student cannot complete/cancel/reschedule sessions

------------------------------------------------------------

## Video link behavior

44. Course has DefaultVideoLink, session VideoLink null:
    - student sees effective video link = course default
45. Session has VideoLink set:
    - student sees session video link
46. Student cannot see course-wide video link outside session context

------------------------------------------------------------

## HomeworkItem (Teacher-managed)

47. Teacher A creates homework item for Active enrollment -> success 
48. Teacher A updates homework status Todo -> Done -> completedAt set 
49. Teacher A sets dueAt, list shows correct ordering (if implemented)
50. Teacher B cannot create homework for Teacher A enrollment 
51. Student sees only his homework in completed + future sessions (Todo/done?) - ученик же видит домашки в сессии да?
52. Enrollment Revoked:
    - Creating new homework is blocked
    - Existing homework remains visible

------------------------------------------------------------

## Security / access boundaries

53. Student S1 cannot access sessions of S2 
54. Student S1 cannot access enrollments directly unless you expose them (if exposed, only own)
55. Teacher A can only see students they enrolled (or via sessions/enrollments)
