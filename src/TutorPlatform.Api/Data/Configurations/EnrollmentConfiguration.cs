using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Data.Configurations;

public class EnrollmentConfiguration : IEntityTypeConfiguration<EnrollmentEntity>
{
    public void Configure(EntityTypeBuilder<EnrollmentEntity> b)
    {
        b.ToTable("enrollments");

        b.HasKey(x => x.Id);

        b.Property(x => x.Plan).HasMaxLength(2000);
        b.Property(x => x.Progress).HasMaxLength(2000);

        b.Property(x => x.Status).HasConversion<int>();

        b.Property(x => x.CreatedAt).IsRequired();
        b.Property(x => x.UpdatedAt).IsRequired();

        b.HasIndex(x => new { x.CourseId, x.StudentId }).IsUnique();

        b.HasOne(x => x.Course)
            .WithMany(c => c.Enrollments)
            .HasForeignKey(x => x.CourseId)
            .OnDelete(DeleteBehavior.Cascade);

        b.HasOne(x => x.Student)
            .WithMany(u => u.Enrollments)
            .HasForeignKey(x => x.StudentId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
