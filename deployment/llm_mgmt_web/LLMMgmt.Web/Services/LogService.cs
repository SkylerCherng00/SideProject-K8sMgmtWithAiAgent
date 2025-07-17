using System.Text.Json;
using LLMMgmtAgent.Web.Models;

namespace LLMMgmtAgent.Web.Services;

public interface ILogService
{
    Task<LabelsResponse> GetLabelsAsync();
    Task<LogQueryResponse> GetLogsAsync(LogQueryRequest request);
    Task<string> GetLogsAsJsonAsync(LogQueryRequest request);
}

public class LogService : ILogService
{
    private readonly HttpClient _httpClient;
    private readonly ApiEndpoints _apiEndpoints;

    public LogService(HttpClient httpClient, ApiEndpoints apiEndpoints)
    {
        _httpClient = httpClient;
        _apiEndpoints = apiEndpoints;
        _httpClient.DefaultRequestHeaders.Add("Accept", "application/json");
    }

    public async Task<LabelsResponse> GetLabelsAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync(_apiEndpoints.LokiLabelsEndpoint);
            
            if (response.IsSuccessStatusCode)
            {
                var jsonContent = await response.Content.ReadAsStringAsync();
                
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                };
                
                return JsonSerializer.Deserialize<LabelsResponse>(jsonContent, options) ?? new LabelsResponse();
            }
            else
            {
                throw new HttpRequestException($"Error fetching labels: {response.StatusCode} - {response.ReasonPhrase}");
            }
        }
        catch (Exception ex)
        {
            throw new Exception($"Failed to fetch labels from Loki API: {ex.Message}", ex);
        }
    }

    public async Task<LogQueryResponse> GetLogsAsync(LogQueryRequest request)
    {
        try
        {
            // Build query URL with parameters
            var queryParams = new Dictionary<string, string>
            {
                { "query", request.Query },
                { "start_time", request.StartTime },
                { "end_time", request.EndTime },
                { "limit", request.Limit.ToString() }
            };
            
            var queryString = string.Join("&", queryParams.Select(kv => $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}"));
            var url = $"{_apiEndpoints.LokiLogsEndpoint}?{queryString}";
            
            var response = await _httpClient.GetAsync(url);
            
            if (response.IsSuccessStatusCode)
            {
                var jsonContent = await response.Content.ReadAsStringAsync();
                
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                };
                
                return JsonSerializer.Deserialize<LogQueryResponse>(jsonContent, options) ?? new LogQueryResponse();
            }
            else
            {
                throw new HttpRequestException($"Error fetching logs: {response.StatusCode} - {response.ReasonPhrase}");
            }
        }
        catch (Exception ex)
        {
            throw new Exception($"Failed to fetch logs from Loki API: {ex.Message}", ex);
        }
    }

    public async Task<string> GetLogsAsJsonAsync(LogQueryRequest request)
    {
        try
        {
            // Build query URL with parameters
            var queryParams = new Dictionary<string, string>
            {
                { "query", request.Query },
                { "start_time", request.StartTime },
                { "end_time", request.EndTime },
                { "limit", request.Limit.ToString() }
            };
            
            var queryString = string.Join("&", queryParams.Select(kv => $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value)}"));
            var url = $"{_apiEndpoints.LokiLogsEndpoint}?{queryString}";
            
            var response = await _httpClient.GetAsync(url);
            
            if (response.IsSuccessStatusCode)
            {
                return await response.Content.ReadAsStringAsync();
            }
            else
            {
                return $"Error: {response.StatusCode} - {response.ReasonPhrase}";
            }
        }
        catch (Exception ex)
        {
            return $"Exception occurred: {ex.Message}";
        }
    }
}