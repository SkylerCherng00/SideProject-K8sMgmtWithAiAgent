using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using LLMMgmtAgent.Web.Services;
using LLMMgmtAgent.Web.Models;

namespace LLMMgmtAgent.Web;

public class Program
{
    public static void Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);
        builder.Services.AddControllersWithViews();
        // Add Session service
        builder.Services.AddSession();
        
        // Register ApiEndpoints as singleton
        builder.Services.AddSingleton<ApiEndpoints>();
        
        // Register HttpClient and API service
        builder.Services.AddHttpClient<IApiService, ApiService>();
        
        // Register Kubernetes service
        builder.Services.AddHttpClient<IKubernetesService, KubernetesService>();
        
        // Register Log service
        builder.Services.AddHttpClient<ILogService, LogService>();

        var app = builder.Build();
        app.UseStaticFiles();
        // Use Session middleware before routing
        app.UseSession();
        app.UseRouting();
        app.MapDefaultControllerRoute();
        app.Run();
    }
}