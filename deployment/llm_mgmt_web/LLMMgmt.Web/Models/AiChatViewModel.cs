using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace LLMMgmtAgent.Web.Models;

// ViewModel for AI Chat page
public class AiChatViewModel
{
    public List<ChatMessage> Messages { get; set; } = new List<ChatMessage>();
    public string UserInput { get; set; }
}

// Represents a single chat message
public class ChatMessage
{
    public string Sender { get; set; } // "User" or "Bot"
    public string Content { get; set; }
}

// Models for API response parsing
public class ApiResponse
{
    public ReplyData reply { get; set; }
    public bool is_safe { get; set; }
    public object details { get; set; }
}

public class ReplyData
{
    public InputData input { get; set; }
    public string output { get; set; }
}

public class InputData
{
    public List<MessageData> messages { get; set; }
}

public class MessageData
{
    public string content { get; set; }
    public Dictionary<string, object> additional_kwargs { get; set; }
    public Dictionary<string, object> response_metadata { get; set; }
    public string type { get; set; }
    public string name { get; set; }
    public string id { get; set; }
}

// Request model for sending messages
public class SendMessageRequest
{
    public string Message { get; set; }
}

// Kubernetes Pod Metrics models (new comprehensive API)
public class PodMetrics
{
    [JsonPropertyName("namespace")]
    public string Namespace { get; set; }
    
    [JsonPropertyName("service")]
    public string Service { get; set; }
    
    [JsonPropertyName("pod")]
    public string Pod { get; set; }
    
    [JsonPropertyName("node")]
    public string Node { get; set; }
    
    /// <summary>
    /// CPU usage metrics - Average CPU utilization of the entire pod in CPU core per second
    /// </summary>
    [JsonPropertyName("cpu")]
    public List<double> Cpu { get; set; } = new List<double>();
    
    /// <summary>
    /// Memory usage metrics - Bytes of memory used by the pod
    /// </summary>
    [JsonPropertyName("mem")]
    public List<double> Mem { get; set; } = new List<double>();
    
    /// <summary>
    /// Network I/O metrics - Bytes received by the pod
    /// </summary>
    [JsonPropertyName("net_in")]
    public List<double> NetIn { get; set; } = new List<double>();
    
    /// <summary>
    /// Network I/O metrics - Bytes transmitted by the pod
    /// </summary>
    [JsonPropertyName("net_out")]
    public List<double> NetOut { get; set; } = new List<double>();
    
    /// <summary>
    /// Pod status information - 1.0 if running, 0.0 if not
    /// </summary>
    [JsonPropertyName("pod_status")]
    public List<double> PodStatus { get; set; } = new List<double>();
}

public class PodMetricsResponse
{
    public Dictionary<string, List<PodMetrics>> Namespaces { get; set; } = new Dictionary<string, List<PodMetrics>>();
}

// Original Kubernetes Pod models (for backward compatibility)
public class KubernetesPod
{
    public string ApiVersion { get; set; }
    public string Kind { get; set; }
    public PodMetadata Metadata { get; set; }
    public PodSpec Spec { get; set; }
    public PodStatus Status { get; set; }
}

public class PodMetadata
{
    public string Name { get; set; }
    public string Namespace { get; set; }
    public string Uid { get; set; }
    public string ResourceVersion { get; set; }
    public DateTime CreationTimestamp { get; set; }
    public Dictionary<string, string> Labels { get; set; } = new Dictionary<string, string>();
    public Dictionary<string, string> Annotations { get; set; } = new Dictionary<string, string>();
}

public class PodSpec
{
    public List<Container> Containers { get; set; } = new List<Container>();
    public string NodeName { get; set; }
    public string RestartPolicy { get; set; }
    public string ServiceAccountName { get; set; }
}

public class Container
{
    public string Name { get; set; }
    public string Image { get; set; }
    public List<string> Command { get; set; } = new List<string>();
    public List<string> Args { get; set; } = new List<string>();
    public List<ContainerPort> Ports { get; set; } = new List<ContainerPort>();
    public List<EnvVar> Env { get; set; } = new List<EnvVar>();
    public ResourceRequirements Resources { get; set; }
}

public class ContainerPort
{
    public int Port { get; set; }
    public string Protocol { get; set; }
    public string Name { get; set; }
}

public class EnvVar
{
    public string Name { get; set; }
    public string Value { get; set; }
}

public class ResourceRequirements
{
    public Dictionary<string, string> Limits { get; set; } = new Dictionary<string, string>();
    public Dictionary<string, string> Requests { get; set; } = new Dictionary<string, string>();
}

public class PodStatus
{
    public string Phase { get; set; }
    public List<ContainerStatus> ContainerStatuses { get; set; } = new List<ContainerStatus>();
    public string PodIP { get; set; }
    public string HostIP { get; set; }
    public DateTime StartTime { get; set; }
    public List<PodCondition> Conditions { get; set; } = new List<PodCondition>();
}

public class ContainerStatus
{
    public string Name { get; set; }
    public bool Ready { get; set; }
    public int RestartCount { get; set; }
    public string Image { get; set; }
    public string ImageID { get; set; }
    public ContainerState State { get; set; }
}

public class ContainerState
{
    public ContainerStateRunning Running { get; set; }
    public ContainerStateWaiting Waiting { get; set; }
    public ContainerStateTerminated Terminated { get; set; }
}

public class ContainerStateRunning
{
    public DateTime StartedAt { get; set; }
}

public class ContainerStateWaiting
{
    public string Reason { get; set; }
    public string Message { get; set; }
}

public class ContainerStateTerminated
{
    public int ExitCode { get; set; }
    public string Reason { get; set; }
    public string Message { get; set; }
    public DateTime StartedAt { get; set; }
    public DateTime FinishedAt { get; set; }
}

public class PodCondition
{
    public string Type { get; set; }
    public string Status { get; set; }
    public DateTime LastProbeTime { get; set; }
    public DateTime LastTransitionTime { get; set; }
    public string Reason { get; set; }
    public string Message { get; set; }
}

public class KubernetesPodsResponse
{
    public string ApiVersion { get; set; }
    public string Kind { get; set; }
    public ListMetadata Metadata { get; set; }
    public List<KubernetesPod> Items { get; set; } = new List<KubernetesPod>();
}

public class ListMetadata
{
    public string ResourceVersion { get; set; }
    public string Continue { get; set; }
}

// Loki Logs Models
public class LogEntry
{
    [JsonPropertyName("timestamp")]
    public string Timestamp { get; set; }

    [JsonPropertyName("log")]
    public string Log { get; set; }
}

public class LogQueryResponse
{
    [JsonPropertyName("stream")]
    public Dictionary<string, object> Stream { get; set; } = new Dictionary<string, object>();

    [JsonPropertyName("values")]
    public List<LogEntry> Values { get; set; } = new List<LogEntry>();
}

public class LabelsResponse
{
    [JsonPropertyName("labels")]
    public Dictionary<string, List<string>> Labels { get; set; } = new Dictionary<string, List<string>>();
}

public class LogsViewModel
{
    public List<LogQueryResponse> LogData { get; set; } = new List<LogQueryResponse>();
    public Dictionary<string, List<string>> AvailableLabels { get; set; } = new Dictionary<string, List<string>>();
    public string CurrentQuery { get; set; }
    public string StartTime { get; set; }
    public string EndTime { get; set; }
    public int Limit { get; set; } = 1000;
    public bool HasError { get; set; }
    public string ErrorMessage { get; set; }
    public int TotalLogs { get; set; }
    public DateTime? LastRefresh { get; set; }
}

public class LogQueryRequest
{
    public string Query { get; set; }
    public string StartTime { get; set; }
    public string EndTime { get; set; }
    public int Limit { get; set; } = 1000;
}
