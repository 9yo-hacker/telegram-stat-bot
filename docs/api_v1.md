# TutorPlatform API (v1)

## Общие правила

### Base URL
`/api`

### Auth
- Все защищённые эндпоинты требуют:
  - `Authorization: Bearer <JWT>`
- Роли:
  - Teacher
  - Student

### Формат ошибок (рекомендация)
- 400 — validation_failed
- 401 — unauthorized
- 403 — forbidden (роль/доступ)
- 404 — not_found (ресурс не найден или нет доступа)
- 409 — conflict (например, уже существует)
- 500 — internal_error (стараемся не допускать, особенно в публичных эндпоинтах)

### Dev only
Эндпоинты `/api/dev/*` работают только в Development окружении.

---

## AUTH (MVP)

### POST /auth/login
**Доступ:** Public  
**Назначение:** логин по email+password

**Body**
- email: string
- password: string

**Response 200**
- accessToken: string

---

### GET /auth/me
**Доступ:** Teacher/Student  
**Назначение:** текущий пользователь

**Response 200**
- id: guid
- role: "Teacher" | "Student"
- email: string
- name: string
- studentCode?: string (только для Student)

---

## Password Reset (MVP)

### POST /auth/password-reset/request
**Доступ:** Public  
**Назначение:** запрос на сброс пароля  
**Важно:** не раскрываем, существует ли email.

**Body**
- email: string

**Response 200**
- token: string | null  
  - В Production: всегда `null`
  - В Development: может быть token для теста (если включено)

---

### POST /auth/password-reset/confirm
**Доступ:** Public  
**Назначение:** подтверждение сброса пароля

**Body**
- token: string
- newPassword: string

**Response 204**
(no content)

**Ошибки**
- 400 invalid_or_expired
- 400 validation_failed

---

## DASHBOARDS (фиксированные, MVP)

### GET /teacher/dashboard
**Доступ:** Teacher  
**Назначение:** фиксированные данные для главной учителя

**Response 200**
- activeCoursesCount: int
- upcomingSessionsCount7d: int
- pendingHomeworksCount: int (если домашек нет — 0)
- nextSession?: {
  - id: guid
  - startsAt: datetime
  - durationMinutes: int
  - courseId: guid
  - courseTitle: string
  - studentId: guid
  - studentName: string
  - videoLinkEffective: string | null
}

---

### GET /student/dashboard
**Доступ:** Student  
**Назначение:** фиксированные данные для главной ученика

**Response 200**
- pendingHomeworksCount: int (если домашек нет — 0)
- nextSession?: {
  - id: guid
  - startsAt: datetime
  - durationMinutes: int
  - courseId: guid
  - courseTitle: string
  - teacherName: string
  - status: "planned" | "done" | "canceled" | "skipped"
  - videoLinkEffective: string | null
}
- upcomingSessions: [
  {
    id: guid
    startsAt: datetime
    durationMinutes: int
    courseId: guid
    courseTitle: string
    status: string
  }
]

---

## TEACHER: COURSES (MVP)

### GET /teacher/courses
**Доступ:** Teacher  
**Query**
- status?: active|archived

**Response 200**
- items: [{ id, title, description?, status, defaultVideoLink?, createdAt, updatedAt }]

---

### POST /teacher/courses
**Доступ:** Teacher

**Body**
- title: string
- description?: string
- defaultVideoLink?: string|null
- status?: active|archived (обычно active)

**Response 201**
- course: { ... }

---

### GET /teacher/courses/{courseId}
**Доступ:** Teacher (только свои)

**Response 200**
- { id, title, description, status, defaultVideoLink, ... }

---

### PATCH /teacher/courses/{courseId}
**Доступ:** Teacher (только свои)  
**Назначение:** частичное обновление

**Body (любые поля)**
- title?
- description?
- defaultVideoLink?
- status?

**Response 200**
- { ...updated }

---

## TEACHER: LESSONS (MVP)

### GET /teacher/courses/{courseId}/lessons
**Доступ:** Teacher (только свои)

**Query**
- status?: draft|published

**Response 200**
- items: [{ id, courseId, title, materialUrl?, status, createdAt, updatedAt }]

---

### POST /teacher/courses/{courseId}/lessons
**Доступ:** Teacher (только свои)

**Body**
- title: string
- materialUrl?: string|null
- status?: draft|published

**Response 201**
- lesson: { ... }

---

### GET /teacher/lessons/{lessonId}
**Доступ:** Teacher (только свои)

**Response 200**
- { id, courseId, title, materialUrl, status, ... }

---

### PATCH /teacher/lessons/{lessonId}
**Доступ:** Teacher (только свои)

**Body**
- title?
- materialUrl?
- status?

**Response 200**
- { ...updated }

---

## TEACHER: ENROLLMENTS / STUDENTS (MVP)

### POST /teacher/courses/{courseId}/enrollments
**Доступ:** Teacher (только свои)  
**Назначение:** добавить ученика в курс по studentCode (9 цифр)

**Body**
- studentCode: string (ровно 9 цифр)

**Response 201**
- enrollment: { id, courseId, studentId, status, createdAt, updatedAt }

**Ошибки**
- 400 validation_failed
- 404 student_not_found
- 409 already_enrolled

---

### GET /teacher/courses/{courseId}/enrollments
**Доступ:** Teacher (только свои)

**Response 200**
- items: [{
  id, courseId, studentId, studentName, studentCode, status
}]

---

### POST /teacher/enrollments/{enrollmentId}/revoke
**Доступ:** Teacher (только свои)

**Response 204**

---

### POST /teacher/enrollments/{enrollmentId}/restore
**Доступ:** Teacher (только свои)

**Response 204**

---

## TEACHER: SESSIONS (MVP)

### GET /teacher/sessions
**Доступ:** Teacher

**Query**
- from?: datetime
- to?: datetime
- courseId?: guid
- studentId?: guid
- status?: planned|done|canceled|skipped

**Response 200**
- items: [{ id, courseId, studentId, startsAt, durationMinutes, status, lessonId?, videoLink?, notes? }]

---

### POST /teacher/sessions
**Доступ:** Teacher  
**Назначение:** создать занятие (MVP-правило: допускаем startsAt в прошлом)

**Body**
- courseId: guid
- studentId: guid
- startsAt: datetime
- durationMinutes: int
- lessonId?: guid|null
- videoLink?: string|null
- notes?: string|null

**Response 201**
- session: { id, ... , status: planned }

**Ошибки**
- 400 validation_failed
- 404 course_not_found / student_not_found
- 400 revoked (если enrollment revoked)

---

### POST /teacher/sessions/{sessionId}/complete
**Доступ:** Teacher (только свои)  
**Назначение:** завершить занятие + snapshot полей урока

**Response 204**
(или 200)

**Ошибки**
- 404 not_found
- 400 cannot_complete_canceled

---

### POST /teacher/sessions/{sessionId}/cancel
**Доступ:** Teacher (только свои)

**Response 204**

---

### POST /teacher/sessions/{sessionId}/skip
**Доступ:** Teacher (только свои)  
**Примечание:** только если статус skipped реально используется

**Response 204**

---

### PATCH /teacher/sessions/{sessionId}
**Доступ:** Teacher (только свои)  
**Назначение:** перенос/изменение данных

**Body**
- startsAt?
- durationMinutes?
- lessonId?
- videoLink?
- notes?

**Response 200**
- updated session

---

## STUDENT: COURSES (MVP)

### GET /student/courses
**Доступ:** Student  
**Назначение:** курсы ученика (только enrollment active)

**Response 200**
- items: [{
  id, title, description?, teacherName, defaultVideoLink?
}]

---

### GET /student/courses/{courseId}
**Доступ:** Student (только свой enrollment)

**Response 200**
- { id, title, description, teacherName, defaultVideoLink? }

---

### GET /student/courses/{courseId}/lessons
**Доступ:** Student (только свой enrollment)  
**Назначение:** уроки курса (обычно только published)

**Query**
- status?: published (по умолчанию published)

**Response 200**
- items: [{ id, title, materialUrl?, status }]

---

## STUDENT: SCHEDULE / SESSIONS (MVP)

### GET /student/sessions
**Доступ:** Student  
**Назначение:** расписание (ключевой экран)

**Query**
- from?: datetime
- to?: datetime
- courseId?: guid
- status?: planned|done|canceled|skipped

**Response 200**
- items: [{
  id, courseId, courseTitle,
  startsAt, durationMinutes,
  status,
  videoLinkEffective
}]

---

### GET /student/sessions/{sessionId}
**Доступ:** Student (только если session принадлежит студенту)

**Response 200**
- {
  id, courseId, courseTitle,
  startsAt, durationMinutes,
  status,
  videoLinkEffective,
  liveLessonMaterialUrl?,              // planned: lesson material url
  lessonTitleSnapshot?,                // done: snapshot
  lessonMaterialUrlSnapshot?,          // done: snapshot
  notes?
}

---

## HOMEWORK (Phase 2, дизайн API заранее)

### GET /student/homeworks
**Доступ:** Student  
**Query**
- tab?: active|checked (active = todo/submitted, checked = done)

**Response 200**
- items: [{
  id, courseId, courseTitle,
  sessionId?, lessonId?,
  title?, taskText,
  status: todo|submitted|done|skipped,
  dueAt?, updatedAt
}]

---

### GET /student/homeworks/{homeworkId}
**Доступ:** Student

**Response 200**
- {
  id, taskText, status, dueAt?,
  answerText?, answerUrl?,
  teacherComment?, score?
}

---

### POST /student/homeworks/{homeworkId}/submit
**Доступ:** Student  
**Body**
- answerText: string
- answerUrl?: string|null

**Response 204**

---

### GET /teacher/homeworks
**Доступ:** Teacher  
**Query**
- status?: todo|submitted|done|skipped
- courseId?: guid
- sessionId?: guid

**Response 200**
- items: [{ id, studentId, studentName, status, dueAt?, updatedAt }]

---

### POST /teacher/sessions/{sessionId}/homework
**Доступ:** Teacher (только свои)

**Body**
- taskText: string
- dueAt?: datetime|null

**Response 201**
- homework: { id, ... }

---

### POST /teacher/homeworks/{homeworkId}/grade
**Доступ:** Teacher (только свои)

**Body**
- status: done|todo|skipped
- score?: int|null
- comment?: string|null

**Response 204**

---

## FINANCE (Phase 2 placeholder)

### GET /teacher/billing/summary
### GET /teacher/billing/transactions
### POST /teacher/billing/payout-method

---

## DEV (Development only)

### POST /dev/seed
**Доступ:** Dev only  
**Headers**
- X-Dev-Seed: 1

**Response 200**
- teacherToken
- studentToken
- teacherId
- studentId
- courseId
- lessonId
- enrollmentId
