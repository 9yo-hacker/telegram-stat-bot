using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace TutorPlatform.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddStudentEndpointsAndHomeworkAnswerFields : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTime>(
                name: "CheckedAt",
                table: "homework_items",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "StudentAnswer",
                table: "homework_items",
                type: "character varying(4000)",
                maxLength: 4000,
                nullable: true);

            migrationBuilder.AddColumn<DateTime>(
                name: "StudentAnswerSubmittedAt",
                table: "homework_items",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "TeacherComment",
                table: "homework_items",
                type: "character varying(4000)",
                maxLength: 4000,
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "TeacherGrade",
                table: "homework_items",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_homework_items_CheckedAt",
                table: "homework_items",
                column: "CheckedAt");

            migrationBuilder.CreateIndex(
                name: "IX_homework_items_StudentAnswerSubmittedAt",
                table: "homework_items",
                column: "StudentAnswerSubmittedAt");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_homework_items_CheckedAt",
                table: "homework_items");

            migrationBuilder.DropIndex(
                name: "IX_homework_items_StudentAnswerSubmittedAt",
                table: "homework_items");

            migrationBuilder.DropColumn(
                name: "CheckedAt",
                table: "homework_items");

            migrationBuilder.DropColumn(
                name: "StudentAnswer",
                table: "homework_items");

            migrationBuilder.DropColumn(
                name: "StudentAnswerSubmittedAt",
                table: "homework_items");

            migrationBuilder.DropColumn(
                name: "TeacherComment",
                table: "homework_items");

            migrationBuilder.DropColumn(
                name: "TeacherGrade",
                table: "homework_items");
        }
    }
}
