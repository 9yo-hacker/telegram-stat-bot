using Microsoft.EntityFrameworkCore;

namespace TutorPlatform.Api.Infrastructure;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<UserEntity> Users => Set<UserEntity>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<UserEntity>(b =>
        {
            b.ToTable("users");
            b.HasKey(x => x.Id);

            b.Property(x => x.Email).IsRequired();
            b.HasIndex(x => x.Email).IsUnique();

            // partial unique index: StudentCode WHERE NOT NULL
            b.HasIndex(x => x.StudentCode)
             .IsUnique()
             .HasFilter("\"StudentCode\" IS NOT NULL"); // EF Core -> PostgreSQL filter

            b.Property(x => x.Role).IsRequired();
            b.Property(x => x.Name).IsRequired();
            b.Property(x => x.CreatedAt).IsRequired();
        });
    }
}
