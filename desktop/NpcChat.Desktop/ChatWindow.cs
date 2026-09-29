using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;

namespace NpcChat.Desktop;

internal sealed class ChatWindow : Window
{
    public readonly WebView2 Browser = new();
    private readonly App owner;
    public const string Origin = "http://127.0.0.1:8003";
    public ChatWindow(App app)
    {
        owner = app; Title = "NPC Chat · 닫으면 위젯으로 돌아가요";
        Width = 440; Height = 740; MinWidth = 360; MinHeight = 480;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Content = Browser;
        Closing += (_, e) => { if (!owner.Exiting) { e.Cancel = true; Hide(); } };
    }
    public async Task Initialize(string token)
    {
        var packaged = File.Exists(Path.Combine(owner.Root, "desktop-package.json"));
        var browserFolder = packaged ? Path.Combine(owner.Root, "runtime", "webview2") : null;
        if (packaged) {
            foreach (System.Collections.DictionaryEntry entry in Environment.GetEnvironmentVariables())
                if (entry.Key.ToString()!.StartsWith("WEBVIEW2_", StringComparison.OrdinalIgnoreCase))
                    Environment.SetEnvironmentVariable(entry.Key.ToString()!, null);
            if (!File.Exists(Path.Combine(browserFolder!, "msedgewebview2.exe")))
                throw new InvalidOperationException("동봉된 채팅 런타임을 찾을 수 없습니다.");
        }
        var environment = await CoreWebView2Environment.CreateAsync(browserFolder, Path.Combine(owner.DataDirectory, "browser"));
        await Browser.EnsureCoreWebView2Async(environment);
        var web = Browser.CoreWebView2;
        web.Settings.AreDevToolsEnabled = false;
        web.Settings.AreDefaultContextMenusEnabled = false;
        web.Settings.AreHostObjectsAllowed = false;
        web.Settings.AreDefaultScriptDialogsEnabled = false;
        web.Settings.IsPasswordAutosaveEnabled = false;
        web.Settings.IsGeneralAutofillEnabled = false;
        web.PermissionRequested += (_, e) => e.State = CoreWebView2PermissionState.Deny;
        web.NewWindowRequested += (_, e) => e.Handled = true;
        web.DownloadStarting += (_, e) => e.Cancel = true;
        web.NavigationStarting += (_, e) => { if (!Local(e.Uri)) e.Cancel = true; };
        web.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All,
                                        CoreWebView2WebResourceRequestSourceKinds.All);
        web.WebResourceRequested += (_, e) => {
            if (Local(e.Request.Uri)) e.Request.Headers.SetHeader("X-NPC-Desktop", token);
            else e.Response = environment.CreateWebResourceResponse(new MemoryStream(), 403, "Blocked", "");
        };
        web.WebMessageReceived += (_, e) => {
            if (!Local(e.Source)) return;
            try {
                using var doc = JsonDocument.Parse(e.WebMessageAsJson);
                var data = doc.RootElement;
                var face = data.GetProperty("face").GetString() ?? "";
                if (!Regex.IsMatch(face, @"^/(faces|characters/cartethyia/faces)/[a-z_]+\.png$")) return;
                var name = face.StartsWith("/characters/") ? "띳띠" : "유이";
                owner.Widget?.SetFace(Path.Combine(owner.Root, "frontend", face.TrimStart('/').Replace('/', Path.DirectorySeparatorChar)), name);
                if (owner.Widget != null) owner.Widget.Status.Text = data.GetProperty("typing").GetBoolean() ? "답장을 생각하고 있어요…" : "여기 있어요";
            } catch (Exception ex) when (ex is JsonException or InvalidOperationException or KeyNotFoundException) { }
        };
        await web.AddScriptToExecuteOnDocumentCreatedAsync("""
            window.addEventListener('DOMContentLoaded', () => {
              let previous = '';
              const send = () => {
                const img = document.getElementById('heroine');
                if (!img?.src) return;
                const payload = { face: new URL(img.src).pathname,
                  typing: document.getElementById('typingIndicator')?.hidden === false };
                const text = JSON.stringify(payload);
                if (text !== previous) { previous = text; window.chrome.webview.postMessage(payload); }
              };
              new MutationObserver(send).observe(document.body, {subtree:true, attributes:true, attributeFilter:['src','hidden']});
              send();
            });
            """);
        var loaded = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        web.NavigationCompleted += (_, e) => {
            if (e.IsSuccess) loaded.TrySetResult();
            else loaded.TrySetException(new InvalidOperationException("채팅 화면 로딩 실패"));
        };
        web.Navigate(Origin + "/#chat/yui");
        await loaded.Task.WaitAsync(TimeSpan.FromSeconds(30));
    }
    private static bool Local(string url) => Uri.TryCreate(url, UriKind.Absolute, out var uri)
        && uri.GetLeftPart(UriPartial.Authority) == Origin;
}
