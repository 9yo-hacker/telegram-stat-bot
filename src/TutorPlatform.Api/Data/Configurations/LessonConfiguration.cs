using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using TutorPlatform.Api.Data.Entities;

public sealed class LessonConfiguration : IEntityTypeConfiguration<LessonEntity>
{
    public ICollection<LessonEntity> Lessons { get; set; } = new List<LessonEntity>();

    public void Configure(EntityTypeBuilder<LessonEntity> builder)
    {
        builder.ToTable("lessons");

        builder.HasKey(x => x.Id);
        builder.Property(x => x.Title).IsRequired().HasMaxLength(256);

        builder.Property(x => x.MaterialUrl).HasMaxLength(2048);

        builder.Property(x => x.Status).IsRequired();

        builder.HasOne(x => x.Course)
            .WithMany(c => c.Lessons)
            .HasForeignKey(x => x.CourseId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
