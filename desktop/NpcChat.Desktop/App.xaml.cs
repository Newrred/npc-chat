using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Web.WebView2.Core;
using Forms = System.Windows.Forms;

namespace NpcChat.Desktop;

public partial class App : Application
{
    public string Root { get; private set; } = "";
    public string DataDirectory { get; private set; } = "";
    public WidgetWindow? Widget { get; private set; }
    public bool Exiting { get; private set; }
    private ChatWindow? chat;
    private Forms.NotifyIcon? tray;
    private Mutex? singleton;
    private RuntimeClient runtime = new();
    private DiagnosticsWindow? diagnostics;
    private bool starting;
    private bool fake;
    private bool available;
    private bool smoke;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var verifyReal = e.Args.Contains("--verify-real");
        smoke = e.Args.Contains("--smoke") || e.Args.Contains("--smoke-widget") || e.Args.Contains("--smoke-real") || verifyReal;
        fake = e.Args.Contains("--smoke") || e.Args.Contains("--smoke-widget") || e.Args.Contains("--fake") || e.Args.Contains("--smoke-retry");
        Root = Option(e.Args, "--root") ?? FindRoot();
        DataDirectory = Option(e.Args, "--data-dir") ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NpcChatDesktop");
        Directory.CreateDirectory(DataDirectory);
        var key = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(DataDirectory).ToUpperInvariant())));
        singleton = new Mutex(true, "Local\\NpcChatDesktop-" + key, out var first);
        if (!first) { MessageBox.Show("이미 실행 중입니다. 작업 표시줄의 트레이 아이콘에서 열어주세요."); Shutdown(); return; }
        diagnostics = new DiagnosticsWindow(this, File.Exists(Path.Combine(Root, "desktop-package.json")));
        Widget = new WidgetWindow(this); Widget.Show();
        tray = new Forms.NotifyIcon { Icon = System.Drawing.SystemIcons.Application, Text = "NPC Chat · 준비 중", Visible = true };
        var menu = new Forms.ContextMenuStrip();
        menu.Items.Add("채팅 열기", null, (_, _) => Dispatcher.Invoke(ShowChat));
        menu.Items.Add("위젯 표시", null, (_, _) => Dispatcher.Invoke(() => { Widget.Show(); Widget.Activate(); }));
        menu.Items.Add("실행 상태 / 문제 해결", null, (_, _) => Dispatcher.Invoke(ShowDiagnostics));
        menu.Items.Add("완전히 종료", null, async (_, _) => await Quit());
        tray.ContextMenuStrip = menu;
        tray.DoubleClick += (_, _) => Dispatcher.Invoke(() => { Widget.Show(); ShowChat(); });
        SessionEnding += (_, _) => { _ = runtime.Stop(); };
        if (e.Args.Contains("--smoke-retry")) { await RetrySmoke(); return; }
        await Retry();
        if (smoke) {
            if (!available) { diagnostics.Save(Path.Combine(DataDirectory, "diagnostics.json")); await Quit(1); return; }
            try {
                if (verifyReal) {
                    CaptureWidget();
                    await File.WriteAllTextAsync(Path.Combine(DataDirectory, "real-ready.json"), "{\"ready\":true,\"webview\":true}");
                    await Quit();
                } else await Smoke(e.Args.Contains("--smoke-widget"));
            } catch (Exception ex) {
                await File.WriteAllTextAsync(Path.Combine(DataDirectory, "smoke-error.txt"), ex.ToString());
                await Quit(1);
            }
        }
    }

    public void ShowDiagnostics() { diagnostics?.Show(); diagnostics?.Activate(); }

    private void Progress(string code)
    {
        if (Exiting) return;
        diagnostics?.Update(code, false);
        if (Widget != null) {
            Widget.Status.Text = DiagnosticsWindow.Messages.GetValueOrDefault(code, "실행 상태 확인 중…");
            Widget.Status.ToolTip = Widget.Status.Text;
        }
    }

    public async Task Retry()
    {
        if (starting || available || Exiting) return;
        starting = true;
        var phase = "configuration";
        string? failure = null;
        await runtime.Stop();
        chat?.Release(); chat = null;
        runtime = new RuntimeClient();
        runtime.Progress += code => Dispatcher.Invoke(() => { phase = code; Progress(code); });
        runtime.UnexpectedExit += () => Dispatcher.Invoke(() => {
            if (starting || Exiting) return;
            available = false;
            if (Widget != null) { Widget.Status.Text = "서버가 종료됐어요"; Widget.ChatButton.IsEnabled = false; }
            diagnostics?.Update("PROCESS_EXITED", true); ShowDiagnostics();
        });
        try {
            Progress("configuration");
            await runtime.Start(Root, DataDirectory, fake);
            if (Exiting) return;
            phase = "chat_loading"; Progress(phase);
            chat = new ChatWindow(this);
            // WebView2 needs a realized WPF window before EnsureCoreWebView2Async.
            chat.ShowActivated = false;
            chat.Show();
            await chat.Initialize(runtime.Token);
            if (Exiting) return;
            chat.Hide();
            available = true; Widget!.ChatButton.IsEnabled = true; Progress("ready");
            tray!.Text = "NPC Chat · 실행 중";
        } catch (Exception ex) {
            failure = phase == "chat_loading" ? "WEBVIEW_FAILED" :
                DiagnosticsWindow.Messages.ContainsKey(ex.Message) ? ex.Message : "START_FAILED";
            await runtime.Stop();
            chat?.Release(); chat = null;
        } finally {
            starting = false;
            if (failure != null && !Exiting) {
                Widget!.Status.Text = "시작 실패 · 메뉴에서 확인"; Widget.ChatButton.IsEnabled = false;
                diagnostics?.Update(failure, true);
                if (!smoke) ShowDiagnostics();
            }
        }
    }

    public void ShowChat()
    {
        if (!available || chat == null) return;
        if (Widget?.PendingCharacter is string character) chat.OpenCharacter(character);
        ChatViewed();
        chat.Show(); chat.WindowState = WindowState.Normal; chat.Activate();
    }
    public void ChatViewed()
    {
        if (!available) return;
        Widget?.ClearReply();
        if (tray != null) tray.Text = "NPC Chat · 실행 중";
    }
    public void NotifyReply(string character)
    {
        Widget?.NotifyReply(character);
        if (tray != null) tray.Text = "NPC Chat · 새 답장이 도착했어요";
    }
    public async Task Quit(int code = 0)
    {
        if (Exiting) return;
        Exiting = true; available = false;
        if (Widget != null) { Widget.Status.Text = "모델과 서버 종료 중…"; Widget.ChatButton.IsEnabled = false; }
        await runtime.Stop();
        chat?.Release(); diagnostics?.Close(); Widget?.Close();
        tray?.Dispose(); singleton?.Dispose(); Shutdown(code);
    }
    private async Task Smoke(bool widgetTest = false)
    {
        var restored = Widget!.Preferences;
        if (widgetTest) {
            Widget.SetPreferences(1.3, true, false);
            var saved = WidgetState.Load(Path.Combine(DataDirectory, "widget.json"));
            if (saved.Scale != 1.3 || !saved.Compact || saved.Topmost) throw new Exception("Widget preferences not persisted");
        }
        ShowChat();
        using var http = new HttpClient(new HttpClientHandler { UseProxy = false });
        if ((int)(await http.GetAsync(ChatWindow.Origin + "/api/live")).StatusCode != 403)
            throw new Exception("Unauthenticated request was accepted");
        await Task.Delay(1000); // Allow initial history restoration before measuring the new turn.
        var before = int.Parse(await chat!.Browser.CoreWebView2.ExecuteScriptAsync(
            "document.querySelectorAll('#chatThread .message-row.assistant:not(.typing-row)').length"));
        if (Widget.PendingCharacter != null) throw new Exception("Restored history must not notify");
        if (widgetTest) chat.Hide();
        // Exercise actual WebView2 fetch + native face update with synthetic input.
        await chat!.Browser.CoreWebView2.ExecuteScriptAsync("""
            (async () => {
              const input = document.getElementById('messageInput');
              input.value = '안녕'; document.getElementById('chatForm').requestSubmit();
            })();
            """);
        var complete = false;
        for (var i = 0; i < 480; i++) {
            await Task.Delay(250);
            var count = int.Parse(await chat.Browser.CoreWebView2.ExecuteScriptAsync(
                "document.querySelectorAll('#chatThread .message-row.assistant:not(.typing-row)').length"));
            if (count > before) { complete = true; break; }
        }
        if (!complete) throw new Exception("Chat UI failed");
        await Task.Delay(300);
        if (widgetTest) {
            if (Widget.PendingCharacter != "default") throw new Exception("Hidden chat reply did not notify");
            CaptureWidget("widget-unread.png");
            ShowChat();
            if (Widget.PendingCharacter != null) throw new Exception("Opening chat must clear unread");
            await File.WriteAllTextAsync(Path.Combine(DataDirectory, "widget-smoke.json"), JsonSerializer.Serialize(new {
                restored, saved = Widget.Preferences, hiddenReply = true, clearedOnOpen = true, historyDidNotNotify = true
            }));
        }
        CaptureWidget();
        using (var capture = File.Create(Path.Combine(DataDirectory, "chat.png")))
            await chat.Browser.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png, capture);
        chat.Close();
        if (chat.IsVisible || !Widget!.IsVisible) throw new Exception("Close must hide chat");
        ShowChat();
        await File.WriteAllTextAsync(Path.Combine(DataDirectory, "smoke.json"), JsonSerializer.Serialize(new {
            chat = complete, nativeFace = Widget.CharacterName.Text, faceSource = Widget.Portrait.Source.ToString(),
            browserVersion = chat.Browser.CoreWebView2.Environment.BrowserVersionString,
            anonymousBlocked = true, hideRestore = chat.IsVisible, restoredAssistantMessages = before
        }));
        await Quit();
    }
    private void CaptureWidget(string filename = "widget.png")
    {
        var bitmap = new RenderTargetBitmap((int)Widget!.ActualWidth, (int)Widget.ActualHeight, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(Widget);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var output = File.Create(Path.Combine(DataDirectory, filename)); encoder.Save(output);
    }
    private async Task RetrySmoke()
    {
        var listener = new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback, 8003);
        try {
            listener.Start();
            await Retry();
            if (available || diagnostics!.LastCode != "PORT_BUSY") throw new Exception("Expected port conflict");
            diagnostics.Save(Path.Combine(DataDirectory, "failure-diagnostics.json"));
            await Task.Delay(200);
            var bitmap = new RenderTargetBitmap((int)diagnostics.ActualWidth, (int)diagnostics.ActualHeight, 96, 96, PixelFormats.Pbgra32);
            bitmap.Render(diagnostics);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (var capture = File.Create(Path.Combine(DataDirectory, "diagnostics.png"))) encoder.Save(capture);
            listener.Stop();
            await Task.WhenAll(Retry(), Retry()); // Repeated clicks must not launch two supervisors.
            if (!available) throw new Exception("Retry did not recover");
            diagnostics.Save(Path.Combine(DataDirectory, "recovered-diagnostics.json"));
            await Smoke();
        } catch (Exception ex) {
            await File.WriteAllTextAsync(Path.Combine(DataDirectory, "smoke-error.txt"), ex.ToString());
            await Quit(1);
        } finally { listener.Stop(); }
    }
    private static string? Option(string[] args, string key)
    {
        var index = Array.IndexOf(args, key);
        return index >= 0 && index + 1 < args.Length ? Path.GetFullPath(args[index + 1]) : null;
    }
    private static string FindRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory != null) {
            if (File.Exists(Path.Combine(directory.FullName, "scripts/desktop_runtime.py")) ||
                File.Exists(Path.Combine(directory.FullName, "desktop-package.json"))) return directory.FullName;
            directory = directory.Parent;
        }
        throw new InvalidOperationException("--root 옵션으로 프로젝트 위치를 지정해 주세요.");
    }
}
