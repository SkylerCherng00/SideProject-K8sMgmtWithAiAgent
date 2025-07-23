Here's a step-by-step guide to creating a clean MVC-style ASP.NET Core project **without** top‑level statements, **without** `Startup.cs`, and **without** using the MVC template—starting completely from scratch using `dotnet` CLI and using the explicit `Program.cs`-only approach:

---

## 🛠️ Step 1: Create an "empty" ASP.NET Core Web App

```bash
dotnet new web -o ClearMvcApp --use-program-main
cd ClearMvcApp
```

This creates a minimal web app. You’ll now replace the minimal API with a full MVC-style setup without templates or `Startup.cs`.

---

## Step 2: Modify `ClearMvcApp.csproj` (optional cleanup)

Ensure your project targets a recent version (e.g., `net8.0`) and explicitly include MVC packages if needed:

```xml
<PropertyGroup>
  <TargetFramework>net8.0</TargetFramework>
</PropertyGroup>
```

No extra package install needed unless you're using Razor views or additional MVC features.

---

## Step 3: Create a fully-fledged `Program.cs`

Here’s a complete `Program.cs` file—without top-level statements or `Startup.cs`:

```csharp
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace ClearMvcApp
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);

            // ① Add MVC services
            builder.Services.AddControllersWithViews();

            var app = builder.Build();

            // ② Configure middleware pipeline
            if (app.Environment.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }
            else
            {
                app.UseExceptionHandler("/Home/Error");
                app.UseHsts();
            }

            app.UseHttpsRedirection();
            app.UseStaticFiles();

            app.UseRouting();

            app.UseAuthorization();

            // ③ Customize endpoint routing for MVC
            app.MapControllerRoute(
                name: "default",
                pattern: "{controller=Home}/{action=Index}/{id?}");

            app.Run();
        }
    }
}
```

**Key points:**

* You're **not** using top-level statements.
* All configuration lives in this single file—no split into `Startup.cs`.
* MVC services and middleware pipeline are explicitly defined—even though the project was created from the empty template ([stackoverflow.com][1], [mobiletonster.com][2]).

---

## Step 4: Add a Controller & a View

Create a `Controllers/HomeController.cs`:

```csharp
using Microsoft.AspNetCore.Mvc;

namespace ClearMvcApp.Controllers
{
    public class HomeController : Controller
    {
        public IActionResult Index()
        {
            ViewData["Message"] = "Welcome to Clear MVC!";
            return View();
        }

        public IActionResult Error()
        {
            return View();
        }
    }
}
```

Create `Views/Home/Index.cshtml`:

```html
@{
    ViewData["Title"] = "Home";
}
<h1>@ViewData["Message"]</h1>
```

Also create an `Error.cshtml` view (basic Razor markup).

---

## Step 5: Enable View Compilation

Ensure your `.csproj` includes:

```xml
<PropertyGroup>
  <TargetFramework>net8.0</TargetFramework>
  <RazorCompileOnBuild>true</RazorCompileOnBuild>
  <RazorCompileOnPublish>true</RazorCompileOnPublish>
</PropertyGroup>
```

---

## Step 6: Run & Test

```bash
dotnet run
```

Navigate to `https://localhost:5001/` and you should see “Welcome to Clear MVC!” from your `HomeController`.

---

## ✅ Why This Works

* **No top-level statements**: You defined a full `Main()` and namespace/class structure.
* **No `Startup.cs`**: You manage DI and middleware in `Program.cs` only.
* **No MVC template used**: You built controller, views, and routing from scratch.
* This reflects the modern hosting pattern where previous `Startup.ConfigureServices()` and `Startup.Configure()` methods are manually integrated into `Program.cs`, replicating with explicit structure ([gist.github.com][3], [mobiletonster.com][2]).

---

## Summary

| Requirement                     | ✅ Included?                                  |
| ------------------------------- | -------------------------------------------- |
| `dotnet` CLI (`dotnet new web`) | ✅ Yes                                        |
| No top‑level statements         | ✅ Yes — with explicit `Program.Main()`       |
| No `Startup.cs` file            | ✅ Configuration is in `Program.cs`           |
| No MVC template used            | ✅ Manually added services, controller, views |

---

## Further Tips

* Want areas, filters, Razor Pages? Inject into `builder.Services` and pipeline before `app.MapControllerRoute(...)`.
* Add authentication, EF Core, etc. by registering via `builder.Services` before `var app = builder.Build();`
* Explore migration guides to understand how MVC patterns changed from .NET 5 to 6–8 ([learn.microsoft.com][4], [stackoverflow.com][1], [gist.github.com][3]).

Let me know if you’d like help with view layouts, partials, static files folders, or wiring EF Core!

[1]: https://stackoverflow.com/questions/78444282/there-is-no-startup-cs-codes-in-dotnet-core-8-what-will-i-do?utm_source=chatgpt.com "There is no startup.cs codes in dotnet core 8. What will I do?"
[2]: https://mobiletonster.com/blog/code/aspnet-core-6-how-to-deal-with-the-missing-startupcs-file?utm_source=chatgpt.com "ASP.NET Core 6 - how to deal with the missing Startup.cs file"
[3]: https://gist.github.com/davidfowl/0e0372c3c1d895c3ce195ba983b1e03d?utm_source=chatgpt.com "NET 6 ASP.NET Core Migration"
[4]: https://learn.microsoft.com/en-us/aspnet/core/tutorials/min-web-api?view=aspnetcore-9.0&utm_source=chatgpt.com "Tutorial: Create a minimal API with ASP.NET Core"
