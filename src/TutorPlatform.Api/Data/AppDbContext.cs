using Microsoft.EntityFrameworkCore;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Data;

public sealed class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) {}

    public DbSet<UserEntity> Users => Set<UserEntity>();
    public DbSet<CourseEntity> Courses => Set<CourseEntity>();
    public DbSet<LessonEntity> Lessons => Set<LessonEntity>();
    public DbSet<EnrollmentEntity> Enrollments => Set<EnrollmentEntity>();
    public DbSet<SessionEntity> Sessions => Set<SessionEntity>();
    public DbSet<HomeworkItemEntity> HomeworkItems => Set<HomeworkItemEntity>();
    public DbSet<PasswordResetTokenEntity> PasswordResetTokens => Set<PasswordResetTokenEntity>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly);
        base.OnModelCreating(modelBuilder);
    }
}
