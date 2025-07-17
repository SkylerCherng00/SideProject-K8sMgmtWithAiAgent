using System;

namespace LLMMgmtAgent.Web.Models;

/// <summary>
/// Centralized storage for all API endpoints used in the application
/// </summary>
public class ApiEndpoints
{
    // Base URLs for different services
    public string LlmBaseUrl { get; set; } = "http://llm_client:10000/llm";
    public string KubernetesBaseUrl { get; set; } = "http://prometheus:10002/prom";
    public string LokiBaseUrl { get; set; } = "http://loki:10001/loki";
    
    // LLM API endpoints
    public string LlmChatEndpoint => $"{LlmBaseUrl}/ask";
    public string LlmK8sAnalysisEndpoint => $"{LlmBaseUrl}/ask_current";
    
    // Kubernetes API endpoints
    public string KubernetesPodsEndpoint => $"{KubernetesBaseUrl}/pods";
    
    // Loki API endpoints
    public string LokiLabelsEndpoint => $"{LokiBaseUrl}/labels";
    public string LokiLogsEndpoint => $"{LokiBaseUrl}/logs";
}