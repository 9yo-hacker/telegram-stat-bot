# README

## Tutor Platform (B2B SaaS for tutors) — MVP

Backend: .NET + PostgreSQL  
MVP focus: courses/lessons (teacher library), enrollments, sessions (planned/live, done/snapshot), homework items.

----------------------------------------------

## Quick start

### 1) Requirements
- .NET SDK 8+
- Docker (for PostgreSQL) or local PostgreSQL

### 2) Run PostgreSQL
```bash
docker compose up -d
```
### 3) Configure environment
Create .env based on .env.example and set values.

### 4) Run backend
```bash
dotnet restore
dotnet run
```
Backend should be available at:
```bash
http://localhost:8080
```

### Docs
- docs/entities.md — entities & rules
- docs/requirements.md — product requirements (MVP)
- docs/api.md — endpoints and access rules (MVP)
- docs/db.md — DB constraints vs app validations
- docs/qa-checklist.md — QA scenarios

### Notes

- No overlap validation for sessions in MVP.
- Students access lesson materials only via sessions.
- Lesson snapshots are stored when a session is completed (Done).