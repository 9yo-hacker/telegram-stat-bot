using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Data.Configurations;

public class SessionConfiguration : IEntityTypeConfiguration<SessionEntity>
{
    public void Configure(EntityTypeBuilder<SessionEntity> b)
    {
        b.ToTable("sessions");

        b.HasKey(x => x.Id);

        b.Property(x => x.Status).HasConversion<int>();

        b.Property(x => x.DurationMinutes).IsRequired();

        b.Property(x => x.VideoLink).HasMaxLength(1000);
        b.Property(x => x.Notes).HasMaxLength(4000);

        b.Property(x => x.LessonTitleSnapshot).HasMaxLength(512);
        b.Property(x => x.LessonMaterialUrlSnapshot).HasMaxLength(2000);

        b.Property(x => x.CreatedAt).IsRequired();
        b.Property(x => x.UpdatedAt).IsRequired();

        // Indexes
        b.HasIndex(x => new { x.TeacherId, x.StartsAt });
        b.HasIndex(x => new { x.StudentId, x.StartsAt });
        b.HasIndex(x => x.CourseId);

        b.HasOne(x => x.Course)
            .WithMany(c => c.Sessions)
            .HasForeignKey(x => x.CourseId)
            .OnDelete(DeleteBehavior.Restrict);

        b.HasOne(x => x.Teacher)
            .WithMany() // можно сделать коллекцию
            .HasForeignKey(x => x.TeacherId)
            .OnDelete(DeleteBehavior.Restrict);

        b.HasOne(x => x.Student)
            .WithMany()
            .HasForeignKey(x => x.StudentId)
            .OnDelete(DeleteBehavior.Restrict);

        // Важно: чтобы урок можно было удалить/архивнуть не ломая историю
        b.HasOne(x => x.Lesson)
            .WithMany()
            .HasForeignKey(x => x.LessonId)
            .OnDelete(DeleteBehavior.SetNull);
    }
}
