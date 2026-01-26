using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Data.Configurations;

public sealed class UserConfiguration : IEntityTypeConfiguration<UserEntity>
{
    public void Configure(EntityTypeBuilder<UserEntity> b)
    {
        b.ToTable("users");

        b.HasKey(x => x.Id);

        b.Property(x => x.Email).IsRequired().HasMaxLength(320);
        b.HasIndex(x => x.Email).IsUnique();

        b.Property(x => x.PasswordHash).IsRequired();
        b.Property(x => x.Name).IsRequired().HasMaxLength(200);

        b.Property(x => x.StudentCode).HasMaxLength(10);

        // Partial unique index (PostgreSQL)
        b.HasIndex(x => x.StudentCode)
            .IsUnique()
            .HasFilter("\"StudentCode\" IS NOT NULL");

        b.Property(x => x.CreatedAt).IsRequired();
        b.Property(x => x.UpdatedAt).IsRequired();
    }
}
