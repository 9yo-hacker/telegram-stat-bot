using System.Linq;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using TutorPlatform.Api.Data;

namespace TutorPlatform.Api.Tests.Shared;

public sealed class ApiFactory : WebApplicationFactory<Program>
{
    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");

        builder.ConfigureServices(services =>
        {
            // Удаляем текущую регистрацию AppDbContext
            var dbOpt = services.SingleOrDefault(d => d.ServiceType == typeof(DbContextOptions<AppDbContext>));
            if (dbOpt != null) services.Remove(dbOpt);

            services.AddDbContext<AppDbContext>(opt =>
            {
                opt.UseInMemoryDatabase("tp-tests");
            });
        });
    }
}
