# README

## Tutor Platform (B2B SaaS for tutors) — MVP

Backend: .NET + PostgreSQL  
MVP focus: courses/lessons (teacher library), enrollments, sessions (planned/live, done/snapshot), homework items.

----------------------------------------------

## Quick start for the first time

### 1) Requirements
- .NET SDK 8+
- EF Core (to work with migration; no need if Db tables will be created manually)
- Docker (for PostgreSQL) or local PostgreSQL

### 2) Download and set the tools before start if absent
Check the version of .NET
- dotnet --list-sdks
Find appropriate version of EF Core (dotnet ef). For example for .NET 8.* you should download 8.* version of EF Core
- dotnet add package Microsoft.EntityFrameworkCore.Design --version 8.0.10
If you want to use EF Core only for the project (locally)
- go to package with project (/tutor-platform)
- dotnet new tool-manifest
- dotnet tool install dotnet-ef --version 8.0.10 (for .NET 8.*)

### 3) Run PostgreSQL
Go to project package (/tutor-platform) and run PostgreSQL

```bash
docker compose up -d
```

Go to src/TutorPlatform.Api

Only for local installation of EF Core

```bash
dotnet tool restore
```

Approve the migration

```bash
dotnet ef database update --context AppDbContext
```

### 4) Run backend
```bash
dotnet run
```
Backend should be available at:
```bash
http://localhost:port
```

To stop the PostgreSQL after stopping the app
```bash
cd ~/tutor-platform
docker compose down
```

## Quick start for daily usage

### 1. Run PostgreSQL
```bash
cd ~/tutor-platform
docker compose up -d
```

### 2. Approve migration (if not done before)
```bash
cd src/TutorPlatform.Api
```
### Only if locally installed dotnet-ef:
```bash
dotnet tool restore
```

### Approve migration (do it every time — safe even if was already made)
```bash
dotnet ef database update --context AppDbContext
```

### 3. Run backend
```bash
dotnet run
```

## 1. To stop backend: press Ctrl+C in terminal

### 2. Stop PostgreSQL (data will be saved)
```bash
cd ~/tutor-platform
docker compose down
```

### If you see errors such as "relation "users" does not exist No migrations were applied. The database is already up to date."
- Stop the app
- go to project package (/tutor-platform)
Clean and delete the Db
- docker compose down -v
- go to src/TutorPlatform.Api 
Remove the EF Core
- dotnet remove package Microsoft.EntityFrameworkCore.Design 
Reinstall EF Core with correct version
- dotnet add package Microsoft.EntityFrameworkCore.Design --version 8.0.10
Remove existing migrations
- rm -f Data/Migrations/*.cs
Go to project package (/tutor-platform)
Run the db
- docker compose up -d
Go to src/TutorPlatform.Api
Create and approve a new migration
- dotnet ef migrations add Init --context AppDbContext
- dotnet ef database update --context AppDbContext
Check if tables like users and courses exists
- docker exec -it tutor-postgres psql -U tutor -d tutor_platform -c '\dt'
Now you can run the app
Go to src/TutorPlatform.Api
- dotnet run

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