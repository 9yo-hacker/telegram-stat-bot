using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Data.Configurations;

public class HomeworkItemConfiguration : IEntityTypeConfiguration<HomeworkItemEntity>
{
    public void Configure(EntityTypeBuilder<HomeworkItemEntity> b)
    {
        b.ToTable("homework_items");
        b.HasKey(x => x.Id);

        b.Property(x => x.Status).HasConversion<int>();

        b.Property(x => x.Title).IsRequired().HasMaxLength(200);
        b.Property(x => x.Description).HasMaxLength(4000);
        b.Property(x => x.LinkUrl).HasMaxLength(2000);

        b.Property(x => x.CreatedAt).IsRequired();
        b.Property(x => x.UpdatedAt).IsRequired();

        b.HasIndex(x => new { x.EnrollmentId, x.Status });
        b.HasIndex(x => x.DueAt);

        b.HasOne(x => x.Enrollment)
            .WithMany(e => e.HomeworkItems)
            .HasForeignKey(x => x.EnrollmentId)
            .OnDelete(DeleteBehavior.Cascade);

        b.HasOne(x => x.CreatedByTeacher)
            .WithMany()
            .HasForeignKey(x => x.CreatedByTeacherId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
