using System.Text.Json;
using System.Text.Json.Serialization;

namespace LLMMgmtAgent.Web.Models;

public class ApiK8sAnalysisResponse
{
    [JsonPropertyName("reply")]
    public ReplyData Reply { get; set; }
    
    [JsonPropertyName("is_safe")]
    public bool IsSafe { get; set; }
    
    [JsonPropertyName("details")]
    public string Details { get; set; }
    
    public class ReplyData
    {
        [JsonPropertyName("input")]
        public InputData Input { get; set; }
        
        [JsonPropertyName("output")]
        [JsonConverter(typeof(OutputDataConverter))]
        public OutputData Output { get; set; }
    }
    
    public class InputData
    {
        [JsonPropertyName("messages")]
        public List<MessageData> Messages { get; set; } = new List<MessageData>();
    }
    
    public class MessageData
    {
        [JsonPropertyName("content")]
        public string Content { get; set; }
        
        [JsonPropertyName("type")]
        public string Type { get; set; }
    }
    
    public class OutputData
    {
        [JsonPropertyName("action")]
        public string Action { get; set; }
        
        [JsonPropertyName("action_input")]
        public string ActionInput { get; set; }
    }
    
    // Custom JSON converter to handle the complex structure of the output field
    public class OutputDataConverter : JsonConverter<OutputData>
    {
        public override OutputData Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            if (reader.TokenType == JsonTokenType.StartObject)
            {
                using (JsonDocument doc = JsonDocument.ParseValue(ref reader))
                {
                    var output = new OutputData();
                    
                    // Try to extract the action
                    if (doc.RootElement.TryGetProperty("action", out JsonElement actionElement))
                    {
                        output.Action = actionElement.GetString();
                    }
                    
                    // Try to extract the action_input
                    if (doc.RootElement.TryGetProperty("action_input", out JsonElement actionInputElement))
                    {
                        // If action_input is a string, use it directly
                        if (actionInputElement.ValueKind == JsonValueKind.String)
                        {
                            output.ActionInput = actionInputElement.GetString();
                        }
                        // If action_input is an object or other type, convert it to a string
                        else
                        {
                            output.ActionInput = actionInputElement.GetRawText();
                        }
                    }
                    
                    return output;
                }
            }
            
            // Handle string input (raw JSON string) for backward compatibility
            if (reader.TokenType == JsonTokenType.String)
            {
                string jsonString = reader.GetString();
                try
                {
                    using (JsonDocument doc = JsonDocument.Parse(jsonString))
                    {
                        var output = new OutputData();
                        
                        if (doc.RootElement.TryGetProperty("action", out JsonElement actionElement))
                        {
                            output.Action = actionElement.GetString();
                        }
                        
                        if (doc.RootElement.TryGetProperty("action_input", out JsonElement actionInputElement))
                        {
                            output.ActionInput = actionInputElement.GetString();
                        }
                        
                        return output;
                    }
                }
                catch
                {
                    // If parsing fails, just use the string as action_input
                    return new OutputData { ActionInput = jsonString };
                }
            }
            
            throw new JsonException($"Unexpected token {reader.TokenType} when deserializing OutputData");
        }

        public override void Write(Utf8JsonWriter writer, OutputData value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            
            if (!string.IsNullOrEmpty(value.Action))
            {
                writer.WriteString("action", value.Action);
            }
            
            if (!string.IsNullOrEmpty(value.ActionInput))
            {
                writer.WriteString("action_input", value.ActionInput);
            }
            
            writer.WriteEndObject();
        }
    }
}