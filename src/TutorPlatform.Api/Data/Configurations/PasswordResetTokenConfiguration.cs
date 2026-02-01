using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using TutorPlatform.Api.Data.Entities;

namespace TutorPlatform.Api.Data.Configurations;

public sealed class PasswordResetTokenConfiguration : IEntityTypeConfiguration<PasswordResetTokenEntity>
{
    public void Configure(EntityTypeBuilder<PasswordResetTokenEntity> b)
    {
        b.ToTable("password_reset_tokens");

        b.HasKey(x => x.Id);

        b.Property(x => x.TokenHash).IsRequired().HasMaxLength(64); // base64 SHA256 обычно 44, но пусть будет запас
        b.HasIndex(x => x.TokenHash).IsUnique();

        b.HasIndex(x => x.UserId);

        b.HasOne(x => x.User)
            .WithMany()
            .HasForeignKey(x => x.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        b.Property(x => x.CreatedAt).IsRequired();
        b.Property(x => x.ExpiresAt).IsRequired();
    }
}
