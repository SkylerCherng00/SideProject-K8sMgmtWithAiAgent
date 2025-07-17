using Microsoft.AspNetCore.Mvc;
using LLMMgmtAgent.Web.Models;
using LLMMgmtAgent.Web.Services;
using System.Collections.Generic;
using System.Text.Json;

namespace LLMMgmtAgent.Web.Controllers;

public class HomeController : Controller
{
    private const string ChatSessionKey = "AiChatMessages";
    private readonly IApiService _apiService;

    public HomeController(IApiService apiService)
    {
        _apiService = apiService;
    }

    // Handles GET /Home/Index (or just / if default route)
    public IActionResult Index()
    {
        return View();
    }

    // Handles GET /Home/AiChat
    public IActionResult AiChat()
    {
        // 從 Session 取得聊天記錄，若無則建立新的
        var messages = HttpContext.Session.Get<List<ChatMessage>>(ChatSessionKey) ?? new List<ChatMessage>();
        var model = new AiChatViewModel { Messages = messages };
        return View(model);
    }

    // Handles POST /Home/AiChat
    [HttpPost]
    public async Task<IActionResult> AiChat(AiChatViewModel model)
    {
        // 取得現有聊天記錄
        var messages = HttpContext.Session.Get<List<ChatMessage>>(ChatSessionKey) ?? new List<ChatMessage>();

        if (!string.IsNullOrWhiteSpace(model.UserInput))
        {
            // 加入使用者訊息
            messages.Add(new ChatMessage { Sender = "User", Content = model.UserInput });
            
            // Call the API service to get AI response
            var apiResponse = await _apiService.SendMessageAsync(model.UserInput);
            
            // Add bot response
            messages.Add(new ChatMessage { Sender = "Bot", Content = apiResponse });
            
            // 更新 Session 中的聊天記錄
            HttpContext.Session.Set(ChatSessionKey, messages);
        }

        // 清空輸入並返回所有訊息
        model.Messages = messages;
        model.UserInput = string.Empty;
        return View(model);
    }

    // New AJAX endpoint for async chat
    [HttpPost]
    public async Task<IActionResult> SendMessage([FromBody] SendMessageRequest request)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(request.Message))
            {
                return Json(new { success = false, error = "Message cannot be empty" });
            }

            // Get existing chat history
            var messages = HttpContext.Session.Get<List<ChatMessage>>(ChatSessionKey) ?? new List<ChatMessage>();

            // Add user message
            messages.Add(new ChatMessage { Sender = "User", Content = request.Message });

            // Call the API service to get AI response
            var apiResponse = await _apiService.SendMessageAsync(request.Message);

            // Add bot response
            messages.Add(new ChatMessage { Sender = "Bot", Content = apiResponse });

            // Update session
            HttpContext.Session.Set(ChatSessionKey, messages);

            return Json(new { success = true, response = apiResponse });
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }
    
    // AJAX endpoint for Kubernetes analysis
    [HttpPost]
    public async Task<IActionResult> AnalyzeK8s()
    {
        try
        {
            // Get the raw JSON response first to check its structure
            var rawJson = await _apiService.GetK8sAnalysisRawAsync();
            
            // Try to extract the report directly from JSON
            try
            {
                using (JsonDocument doc = JsonDocument.Parse(rawJson))
                {
                    // Check if we can extract the action_input directly
                    var actionInput = doc.RootElement
                        .GetProperty("reply")
                        .GetProperty("output")
                        .GetProperty("action_input")
                        .GetString();
                        
                    if (!string.IsNullOrEmpty(actionInput))
                    {
                        return Json(new { success = true, report = actionInput });
                    }
                }
            }
            catch
            {
                // If direct extraction fails, fall back to the structured approach
            }
            
            // Fall back to the original structured approach
            var analysisResponse = await _apiService.GetK8sAnalysisAsync();
            
            if (analysisResponse != null && analysisResponse.IsSafe && 
                analysisResponse.Reply?.Output?.ActionInput != null)
            {
                return Json(new { 
                    success = true, 
                    report = analysisResponse.Reply.Output.ActionInput
                });
            }
            else
            {
                return Json(new { 
                    success = false, 
                    error = analysisResponse.Details ?? "Failed to get K8s analysis"
                });
            }
        }
        catch (Exception ex)
        {
            return Json(new { success = false, error = ex.Message });
        }
    }
    
    // Debug endpoint to get the raw JSON response
    [HttpGet]
    public async Task<IActionResult> DebugK8sAnalysis()
    {
        var rawJson = await _apiService.GetK8sAnalysisRawAsync();
        return Content(rawJson, "application/json");
    }
}

public class SendMessageRequest
{
    public string Message { get; set; }
}
