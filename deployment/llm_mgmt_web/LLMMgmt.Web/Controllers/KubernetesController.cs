using Microsoft.AspNetCore.Mvc;
using LLMMgmtAgent.Web.Models;
using LLMMgmtAgent.Web.Services;
using System.Text.Json;

namespace LLMMgmtAgent.Web.Controllers;

public class KubernetesController : Controller
{
    private readonly IKubernetesService _kubernetesService;
    private readonly ILogService _logService;
    private readonly ApiEndpoints _apiEndpoints;

    public KubernetesController(IKubernetesService kubernetesService, ILogService logService, ApiEndpoints apiEndpoints)
    {
        _kubernetesService = kubernetesService;
        _logService = logService;
        _apiEndpoints = apiEndpoints;
    }

    // GET: /Kubernetes/Pods - Main dashboard view
    public async Task<IActionResult> Pods()
    {
        try
        {
            var metrics = await _kubernetesService.GetPodMetricsAsync();
            
            // Add debug information
            ViewBag.Debug = $"Namespaces count: {metrics.Namespaces.Count}";
            ViewBag.DebugData = string.Join(", ", metrics.Namespaces.Keys);
            
            return View(metrics);
        }
        catch (Exception ex)
        {
            ViewBag.Error = ex.Message;
            ViewBag.Debug = $"Exception occurred: {ex.Message}";
            return View(new PodMetricsResponse());
        }
    }

    // GET: /Kubernetes/TestApi - Test API connection
    public async Task<IActionResult> TestApi()
    {
        try
        {
            var rawJson = await _kubernetesService.GetPodMetricsAsJsonAsync();
            
            ViewBag.ApiUrl = _apiEndpoints.KubernetesPodsEndpoint;
            ViewBag.RawResponse = rawJson;
            
            // Try to parse as metrics
            try
            {
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                };
                var parsed = JsonSerializer.Deserialize<Dictionary<string, List<PodMetrics>>>(rawJson, options);
                ViewBag.ParsedData = parsed;
                ViewBag.ParseSuccess = true;
            }
            catch (Exception parseEx)
            {
                ViewBag.ParseError = parseEx.Message;
                ViewBag.ParseSuccess = false;
            }
            
            return View();
        }
        catch (Exception ex)
        {
            ViewBag.Error = ex.Message;
            return View();
        }
    }

    // GET: /Kubernetes/GetPodMetrics (API endpoint for metrics)
    [HttpGet]
    public async Task<IActionResult> GetPodMetrics()
    {
        try
        {
            var metrics = await _kubernetesService.GetPodMetricsAsync();
            return Json(new { success = true, data = metrics });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }

    // GET: /Kubernetes/GetPodMetricsRaw (API endpoint for raw metrics JSON)
    [HttpGet]
    public async Task<IActionResult> GetPodMetricsRaw()
    {
        try
        {
            var rawJson = await _kubernetesService.GetPodMetricsAsJsonAsync();
            return Content(rawJson, "application/json");
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }

    // GET: /Kubernetes/GetPods (API endpoint) - Legacy support
    [HttpGet]
    public async Task<IActionResult> GetPods()
    {
        try
        {
            var pods = await _kubernetesService.GetPodsListAsync();
            return Json(new { success = true, data = pods });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }

    // GET: /Kubernetes/GetPodsRaw (API endpoint for raw JSON) - Legacy support
    [HttpGet]
    public async Task<IActionResult> GetPodsRaw()
    {
        try
        {
            var rawJson = await _kubernetesService.GetPodsAsJsonAsync();
            return Content(rawJson, "application/json");
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }

    // GET: /Kubernetes/PodDetails/{podName} - Legacy support
    [HttpGet]
    public async Task<IActionResult> PodDetails(string podName)
    {
        try
        {
            var pods = await _kubernetesService.GetPodsListAsync();
            var pod = pods.FirstOrDefault(p => p.Metadata.Name == podName);
            
            if (pod == null)
            {
                return NotFound($"Pod '{podName}' not found");
            }

            return Json(new { success = true, data = pod });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }

    // GET: /Kubernetes/DebugApi - Debug API connection
    [HttpGet]
    public async Task<IActionResult> DebugApi()
    {
        try
        {
            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            
            // Test raw API call
            var rawJson = await _kubernetesService.GetPodMetricsAsJsonAsync();
            var rawCallTime = stopwatch.ElapsedMilliseconds;
            
            stopwatch.Restart();
            
            // Test parsed API call
            var metrics = await _kubernetesService.GetPodMetricsAsync();
            var parsedCallTime = stopwatch.ElapsedMilliseconds;
            
            return Json(new { 
                success = true, 
                rawCallTime = rawCallTime,
                parsedCallTime = parsedCallTime,
                rawResponseLength = rawJson.Length,
                namespaceCount = metrics.Namespaces.Count,
                totalPods = metrics.Namespaces.Values.SelectMany(x => x).Count(),
                rawResponse = rawJson.Length > 1000 ? rawJson.Substring(0, 1000) + "..." : rawJson,
                parsedData = metrics
            });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message, stackTrace = ex.StackTrace });
        }
    }

    // GET: /Kubernetes/Logs - Logs dashboard view
    public async Task<IActionResult> Logs()
    {
        var viewModel = new LogsViewModel
        {
            StartTime = DateTime.Now.AddHours(-1).ToString("yyyy-MM-dd HH:mm:ss"),
            EndTime = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
            Limit = 100
        };
        
        try
        {
            // Get available labels
            var labelsResponse = await _logService.GetLabelsAsync();
            viewModel.AvailableLabels = labelsResponse.Labels;
            return View(viewModel);
        }
        catch (Exception ex)
        {
            viewModel.HasError = true;
            viewModel.ErrorMessage = $"Failed to load labels: {ex.Message}";
            return View(viewModel);
        }
    }

    // POST: /Kubernetes/Logs - Query logs
    [HttpPost]
    public async Task<IActionResult> Logs(LogQueryRequest request)
    {
        var viewModel = new LogsViewModel
        {
            CurrentQuery = request.Query,
            StartTime = request.StartTime,
            EndTime = request.EndTime,
            Limit = request.Limit,
            LastRefresh = DateTime.Now
        };

        try
        {
            // Get logs based on request
            var logsResponse = await _logService.GetLogsAsync(request);
            viewModel.LogData = new List<LogQueryResponse> { logsResponse };
            viewModel.TotalLogs = logsResponse.Values?.Count ?? 0;

            // Get available labels
            var labelsResponse = await _logService.GetLabelsAsync();
            viewModel.AvailableLabels = labelsResponse.Labels;

            return View(viewModel);
        }
        catch (Exception ex)
        {
            viewModel.HasError = true;
            viewModel.ErrorMessage = $"Failed to query logs: {ex.Message}";
            
            try
            {
                // Attempt to retrieve labels even if log query fails
                var labelsResponse = await _logService.GetLabelsAsync();
                viewModel.AvailableLabels = labelsResponse.Labels;
            }
            catch
            {
                // Ignore any exceptions while fetching labels
            }
            
            return View(viewModel);
        }
    }

    // GET: /Kubernetes/GetLabels (API endpoint)
    [HttpGet]
    public async Task<IActionResult> GetLabels()
    {
        try
        {
            var labels = await _logService.GetLabelsAsync();
            return Json(new { success = true, data = labels });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }

    // POST: /Kubernetes/GetLogs (API endpoint)
    [HttpPost]
    public async Task<IActionResult> GetLogs([FromBody] LogQueryRequest request)
    {
        try
        {
            var logs = await _logService.GetLogsAsync(request);
            return Json(new { 
                success = true, 
                data = logs,
                totalLogs = logs.Values?.Count ?? 0,
                queryTime = DateTime.Now
            });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }
}