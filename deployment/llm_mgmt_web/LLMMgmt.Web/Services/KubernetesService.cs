using System.Text.Json;
using LLMMgmtAgent.Web.Models;

namespace LLMMgmtAgent.Web.Services;

public interface IKubernetesService
{
    Task<KubernetesPodsResponse> GetPodsAsync();
    Task<List<KubernetesPod>> GetPodsListAsync();
    Task<string> GetPodsAsJsonAsync();
    Task<PodMetricsResponse> GetPodMetricsAsync();
    Task<string> GetPodMetricsAsJsonAsync();
}

public class KubernetesService : IKubernetesService
{
    private readonly HttpClient _httpClient;
    private readonly ApiEndpoints _apiEndpoints;

    public KubernetesService(HttpClient httpClient, ApiEndpoints apiEndpoints)
    {
        _httpClient = httpClient;
        _apiEndpoints = apiEndpoints;
        _httpClient.DefaultRequestHeaders.Add("Accept", "application/json");
    }

    public async Task<KubernetesPodsResponse> GetPodsAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync(_apiEndpoints.KubernetesPodsEndpoint);
            
            if (response.IsSuccessStatusCode)
            {
                var jsonContent = await response.Content.ReadAsStringAsync();
                
                var options = new JsonSerializerOptions
                {
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                    PropertyNameCaseInsensitive = true
                };
                
                return JsonSerializer.Deserialize<KubernetesPodsResponse>(jsonContent, options);
            }
            else
            {
                throw new HttpRequestException($"Error fetching pods: {response.StatusCode} - {response.ReasonPhrase}");
            }
        }
        catch (Exception ex)
        {
            throw new Exception($"Failed to fetch pods from Kubernetes API: {ex.Message}", ex);
        }
    }

    public async Task<List<KubernetesPod>> GetPodsListAsync()
    {
        var response = await GetPodsAsync();
        return response?.Items ?? new List<KubernetesPod>();
    }

    public async Task<string> GetPodsAsJsonAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync(_apiEndpoints.KubernetesPodsEndpoint);
            
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

    public async Task<PodMetricsResponse> GetPodMetricsAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync(_apiEndpoints.KubernetesPodsEndpoint);
            
            if (response.IsSuccessStatusCode)
            {
                var jsonContent = await response.Content.ReadAsStringAsync();
                
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                };
                
                // Parse as dictionary with namespaces as keys
                var rawData = JsonSerializer.Deserialize<Dictionary<string, List<PodMetrics>>>(jsonContent, options);
                
                return new PodMetricsResponse { Namespaces = rawData ?? new Dictionary<string, List<PodMetrics>>() };
            }
            else
            {
                throw new HttpRequestException($"Error fetching pod metrics: {response.StatusCode} - {response.ReasonPhrase}");
            }
        }
        catch (Exception ex)
        {
            throw new Exception($"Failed to fetch pod metrics from Kubernetes API: {ex.Message}", ex);
        }
    }

    public async Task<string> GetPodMetricsAsJsonAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync(_apiEndpoints.KubernetesPodsEndpoint);
            
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