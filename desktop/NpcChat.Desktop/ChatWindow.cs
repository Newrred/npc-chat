using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shell;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;

namespace NpcChat.Desktop;

internal sealed class ChatWindow : Window
{
    public readonly WebView2 Browser = new();
    public readonly ChatShell Shell = new();
    private readonly App owner;
    private bool releasing;
    private readonly HashSet<string> notified = new();
    private readonly Queue<string> notificationOrder = new();
    public const string Origin = "http://127.0.0.1:8003";
    public ChatWindow(App app)
    {
        owner = app; Title = "NPC Chat · 닫으면 위젯으로 돌아가요";
        Width = 440; Height = 740; MinWidth = 360; MinHeight = 480;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        WindowStyle = WindowStyle.None;
        ResizeMode = ResizeMode.CanResize;
        Background = new SolidColorBrush(Color.FromRgb(245, 247, 242));
        WindowChrome.SetWindowChrome(this, new WindowChrome {
            CaptionHeight = 35, ResizeBorderThickness = new Thickness(6),
            GlassFrameThickness = new Thickness(0), CornerRadius = new CornerRadius(0), UseAeroCaptionButtons = false
        });
        Shell.BrowserHost.Content = Browser;
        Content = Shell;
        StateChanged += (_, _) => {
            // A maximized borderless window must keep its controls inside the work area.
            Shell.Margin = WindowState == WindowState.Maximized ? new Thickness(SystemParameters.ResizeFrameVerticalBorderWidth + SystemParameters.FixedFrameVerticalBorderWidth) : new Thickness(0);
            Shell.MaximizeButton.ToolTip = WindowState == WindowState.Maximized ? "이전 크기로 복원" : "최대화";
        };
        PreviewKeyDown += (_, e) => { if (e.Key == Key.Escape && !Browser.IsKeyboardFocusWithin) { e.Handled = true; Hide(); } };
        Activated += (_, _) => owner.ChatViewed();
        Closing += (_, e) => { if (!owner.Exiting && !releasing) { e.Cancel = true; Hide(); } };
    }
    public void Release() { releasing = true; Browser.Dispose(); Close(); }
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
                if (data.TryGetProperty("kind", out var action) && action.GetString() == "hide") { Hide(); return; }
                if (data.TryGetProperty("kind", out var kind) && kind.GetString() == "reply") {
                    var character = data.GetProperty("character").GetString();
                    var turn = data.GetProperty("turn").GetString();
                    if (character is not ("default" or "cartethyia") || !Guid.TryParse(turn, out var parsedTurn)) return;
                    var key = character + ":" + turn;
                    if (!notified.Add(key)) return;
                    notificationOrder.Enqueue(key);
                    if (notificationOrder.Count > 256) notified.Remove(notificationOrder.Dequeue());
                    var reply = data.TryGetProperty("reply", out var text) && text.ValueKind == JsonValueKind.String ? text.GetString() ?? "" : "";
                    if (!IsVisible || WindowState == WindowState.Minimized) owner.NotifyReply(character, reply);
                    return;
                }
                var face = data.GetProperty("face").GetString() ?? "";
                if (!Regex.IsMatch(face, @"^/(faces|characters/cartethyia/faces)/[a-z_]+\.png$")) return;
                var name = face.StartsWith("/characters/") ? "띳띠" : "유이";
                owner.Widget?.SetFace(Path.Combine(owner.Root, "frontend", face.TrimStart('/').Replace('/', Path.DirectorySeparatorChar)), name);
                if (owner.Widget != null) owner.Widget.Status.Text = data.TryGetProperty("status", out var status) ? status.GetString() ?? "여기 있어요" : "여기 있어요";
            } catch (Exception ex) when (ex is JsonException or InvalidOperationException or KeyNotFoundException) { }
        };
        await web.AddScriptToExecuteOnDocumentCreatedAsync("""
            window.addEventListener('DOMContentLoaded', () => {
              document.documentElement.classList.add('desktop-shell');
              let previous = '';
              const send = () => {
                const img = document.getElementById('heroine');
                if (!img?.src) return;
                const payload = { face: new URL(img.src).pathname,
                  typing: document.getElementById('typingIndicator')?.hidden === false,
                  status: document.getElementById('chatStatus')?.textContent || '여기 있어요' };
                const text = JSON.stringify(payload);
                if (text !== previous) { previous = text; window.chrome.webview.postMessage(payload); }
              };
              new MutationObserver(send).observe(document.body, {subtree:true, childList:true, characterData:true, attributes:true, attributeFilter:['src','hidden']});
              send();
            });
            window.addEventListener('npc-reply-committed', event => {
              window.chrome.webview.postMessage({kind:'reply', character:event.detail.character, turn:event.detail.turn, reply:event.detail.reply});
            });
            document.addEventListener('keydown', event => {
              if (event.key === 'Escape' && !event.isComposing && event.keyCode !== 229 && !document.querySelector('dialog[open]')) {
                event.preventDefault(); window.chrome.webview.postMessage({kind:'hide'});
              }
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
    public async Task<string> SendQuick(string message)
    {
        var result = await Browser.CoreWebView2.ExecuteScriptAsync("window.npcDesktopSend?.(" + JsonSerializer.Serialize(message) + ") ?? 'unavailable'");
        return JsonSerializer.Deserialize<string>(result) ?? "unavailable";
    }
    public void OpenCharacter(string character)
    {
        var route = character == "cartethyia" ? "cartethyia" : "yui";
        _ = Browser.CoreWebView2.ExecuteScriptAsync("window.location.hash = '#chat/" + route + "'");
    }
}
