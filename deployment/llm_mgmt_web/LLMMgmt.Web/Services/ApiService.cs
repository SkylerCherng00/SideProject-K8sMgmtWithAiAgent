using System.Text;
using System.Text.Json;
using LLMMgmtAgent.Web.Models;

namespace LLMMgmtAgent.Web.Services;

public interface IApiService
{
    Task<string> SendMessageAsync(string message);
    Task<ApiK8sAnalysisResponse> GetK8sAnalysisAsync();
    Task<string> GetK8sAnalysisRawAsync(); // Add raw JSON retrieval method for debugging
}

public class ApiService : IApiService
{
    private readonly HttpClient _httpClient;
    private readonly ApiEndpoints _apiEndpoints;

    public ApiService(HttpClient httpClient, ApiEndpoints apiEndpoints)
    {
        _httpClient = httpClient;
        _apiEndpoints = apiEndpoints;
    }

    public async Task<string> SendMessageAsync(string message)
    {
        try
        {
            // Create the request payload
            var payload = new { message = message };
            var jsonContent = JsonSerializer.Serialize(payload);
            
            // Create HTTP content with proper headers
            var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");
            
            // Send the request
            var response = await _httpClient.PostAsync(_apiEndpoints.LlmChatEndpoint, content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseContent = await response.Content.ReadAsStringAsync();
                
                // Parse the JSON response and extract the output field
                try
                {
                    var apiResponse = JsonSerializer.Deserialize<ApiResponse>(responseContent, new JsonSerializerOptions
                    {
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                    });
                    
                    // Return only the output content
                    return apiResponse?.reply?.output ?? "No output received from API";
                }
                catch (JsonException ex)
                {
                    // If JSON parsing fails, return the raw response
                    return $"JSON parsing error: {ex.Message}\nRaw response: {responseContent}";
                }
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
    
    // For debugging - returns raw JSON response
    public async Task<string> GetK8sAnalysisRawAsync()
    {
        try
        {
            var payload = new { message = "What is the current status of our Kubernetes cluster over the last 30 minutes? Are there any alerts, critical errors, or significant resource utilization issues?" };
            var jsonContent = JsonSerializer.Serialize(payload);
            var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync(_apiEndpoints.LlmK8sAnalysisEndpoint, content);
            
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
    
    public async Task<ApiK8sAnalysisResponse> GetK8sAnalysisAsync()
    {
        try
        {
            // Create the predefined request payload for K8s analysis
            var payload = new { message = "What is the current status of our Kubernetes cluster over the last 30 minutes? Are there any alerts, critical errors, or significant resource utilization issues?" };
            var jsonContent = JsonSerializer.Serialize(payload);
            
            // Create HTTP content with proper headers
            var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");
            
            // Send the request
            var response = await _httpClient.PostAsync(_apiEndpoints.LlmK8sAnalysisEndpoint, content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseContent = await response.Content.ReadAsStringAsync();
                
                // Parse the JSON response
                try
                {
                    // Enable better JSON deserialization options for complex JSON
                    var options = new JsonSerializerOptions
                    {
                        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                        PropertyNameCaseInsensitive = true,
                        AllowTrailingCommas = true,
                        ReadCommentHandling = JsonCommentHandling.Skip
                    };
                    
                    var apiResponse = JsonSerializer.Deserialize<ApiK8sAnalysisResponse>(responseContent, options);
                    return apiResponse ?? new ApiK8sAnalysisResponse();
                }
                catch (JsonException ex)
                {
                    // If JSON parsing fails, return an error response
                    return new ApiK8sAnalysisResponse
                    {
                        IsSafe = false,
                        Details = $"JSON parsing error: {ex.Message}"
                    };
                }
            }
            else
            {
                return new ApiK8sAnalysisResponse
                {
                    IsSafe = false,
                    Details = $"Error: {response.StatusCode} - {response.ReasonPhrase}"
                };
            }
        }
        catch (Exception ex)
        {
            return new ApiK8sAnalysisResponse
            {
                IsSafe = false,
                Details = $"Exception occurred: {ex.Message}"
            };
        }
    }
}