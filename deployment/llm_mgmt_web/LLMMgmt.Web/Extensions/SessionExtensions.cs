using System.Text.Json;
using Microsoft.AspNetCore.Http;

namespace LLMMgmtAgent.Web;

/// <summary>
/// Extension methods for ISession to handle complex object serialization
/// </summary>
public static class SessionExtensions
{
    /// <summary>
    /// Sets a complex object in session after serializing it to JSON
    /// </summary>
    public static void Set<T>(this ISession session, string key, T value)
    {
        session.SetString(key, JsonSerializer.Serialize(value));
    }

    /// <summary>
    /// Gets a complex object from session by deserializing it from JSON
    /// </summary>
    public static T? Get<T>(this ISession session, string key)
    {
        var value = session.GetString(key);
        return value == null ? default : JsonSerializer.Deserialize<T>(value);
    }
}