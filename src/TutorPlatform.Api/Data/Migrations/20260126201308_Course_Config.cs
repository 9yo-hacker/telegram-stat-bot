using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace TutorPlatform.Api.Migrations
{
    /// <inheritdoc />
    public partial class Course_Config : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "Status",
                table: "courses",
                type: "integer",
                nullable: false,
                defaultValue: 0);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Status",
                table: "courses");
        }
    }
}
