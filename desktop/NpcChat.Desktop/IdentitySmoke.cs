using System;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Web.WebView2.Core;

namespace NpcChat.Desktop;

public partial class App
{
    // Real WebView2 + native window checks, run only by the isolated widget smoke.
    private async Task VerifyIdentityUi()
    {
        var web = chat!.Browser.CoreWebView2;
        async Task Check(string expression, string failure)
        {
            if (await web.ExecuteScriptAsync(expression) != "true") throw new Exception(failure);
        }
        async Task Capture(string name)
        {
            await Task.Delay(350);
            using var file = File.Create(Path.Combine(DataDirectory, name));
            await web.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png, file);
        }
        chat.Width = 440; chat.Height = 740;
        await Task.Delay(350);
        await Check("getComputedStyle(document.querySelector('.user .bubble')).backgroundColor === 'rgb(116, 52, 255)'", "Violet theme was not loaded");
        await Check("document.querySelectorAll('.relationship-stat').length === 5", "Server relationship not rendered");
        await Capture("identity-compact.png");
        await web.ExecuteScriptAsync("document.getElementById('messageInput').value='보존할 초안'; document.getElementById('expandChat').click()");
        await Task.Delay(450);
        if (chat.ActualWidth < 760) throw new Exception("Expand button did not resize native window");
        await Check("document.getElementById('messageInput').value === '보존할 초안' && getComputedStyle(document.querySelector('.chat-workspace')).flexDirection === 'row'", "Expanded layout lost draft or sidebar");
        await Capture("identity-expanded.png");
        await web.ExecuteScriptAsync("document.getElementById('expandChat').click()");
        await Task.Delay(450);
        if (chat.ActualWidth >= 760) throw new Exception("Collapse button failed");
        await Check("document.getElementById('messageInput').value === '보존할 초안'", "Collapse lost draft");
        await web.ExecuteScriptAsync("document.getElementById('messageInput').value=''; document.getElementById('suggestToday').click()");
        await Check("document.getElementById('messageInput').value === '오늘은 어떻게 보냈어?'", "Suggestion did not fill composer");
        await web.ExecuteScriptAsync("document.getElementById('suggestRest').click()");
        await Check("document.getElementById('messageInput').value === '오늘은 어떻게 보냈어?'", "Suggestion overwrote draft");
        chat.Width = 360; chat.Height = 480;
        await Task.Delay(350);
        await Check("(() => { const r=document.getElementById('chatForm').getBoundingClientRect(); return r.width>0 && r.bottom<=innerHeight && r.right<=innerWidth && document.documentElement.scrollWidth<=innerWidth; })()", "Minimum-size composer overflow");
        await Capture("identity-minimum.png");
        await web.ExecuteScriptAsync("document.getElementById('joinVideo').click()");
        await Task.Delay(350);
        await Check("(() => { const r=document.getElementById('chatForm').getBoundingClientRect(); return !document.getElementById('videoStage').hidden && r.bottom<=innerHeight && r.top>=0; })()", "Portrait obscured minimum-size composer");
        await Capture("identity-portrait.png");
        await web.ExecuteScriptAsync("document.getElementById('endVideo').click()");
        await web.ExecuteScriptAsync("document.getElementById('chatOptions').open=true");
        await Check("(() => { const r=document.getElementById('leaveRoom').getBoundingClientRect(); return r.bottom<=innerHeight && r.top>=0; })()", "Settings inaccessible at minimum size");
        await Capture("identity-settings.png");
        await web.ExecuteScriptAsync("document.getElementById('chatOptions').open=false; document.getElementById('messageInput').value=''; document.getElementById('backToList').click()");
        await Task.Delay(350);
        await Check("!document.getElementById('conversationList').hidden", "Conversation navigation failed");
        chat.Width = 440; chat.Height = 740;
        await Capture("identity-rooms.png");
        await web.ExecuteScriptAsync("document.getElementById('openCartethyiaRoom').click()");
        await Task.Delay(450);
        await Check("document.getElementById('companionName').textContent === '띳띠' && document.getElementById('relationshipStats').hidden", "Character switch leaked previous relationship");
        await web.ExecuteScriptAsync("document.getElementById('backToList').click()");
        await Task.Delay(150);
        await web.ExecuteScriptAsync("document.getElementById('openYuiRoom').click()");
        await Task.Delay(500);
        await Check("document.querySelectorAll('.relationship-stat').length === 5", "Relationship did not restore from history");
        await File.WriteAllTextAsync(Path.Combine(DataDirectory, "identity-smoke.json"), "{\"compact\":true,\"expanded\":true,\"draftPreserved\":true,\"minimumSize\":true,\"settings\":true,\"characterIsolation\":true,\"serverRelationshipRestored\":true}");
    }
}
