using System;
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
    private readonly RuntimeClient runtime = new();
    private bool available;
    private bool smoke;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var verifyReal = e.Args.Contains("--verify-real");
        smoke = e.Args.Contains("--smoke") || e.Args.Contains("--smoke-real") || verifyReal;
        Root = Option(e.Args, "--root") ?? FindRoot();
        DataDirectory = Option(e.Args, "--data-dir") ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NpcChatDesktop");
        Directory.CreateDirectory(DataDirectory);
        var key = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(DataDirectory).ToUpperInvariant())));
        singleton = new Mutex(true, "Local\\NpcChatDesktop-" + key, out var first);
        if (!first) { MessageBox.Show("이미 실행 중입니다. 작업 표시줄의 트레이 아이콘에서 열어주세요."); Shutdown(); return; }
        Widget = new WidgetWindow(this); Widget.Show();
        tray = new Forms.NotifyIcon { Icon = System.Drawing.SystemIcons.Application, Text = "NPC Chat · 준비 중", Visible = true };
        var menu = new Forms.ContextMenuStrip();
        menu.Items.Add("채팅 열기", null, (_, _) => Dispatcher.Invoke(ShowChat));
        menu.Items.Add("위젯 표시", null, (_, _) => Dispatcher.Invoke(() => { Widget.Show(); Widget.Activate(); }));
        menu.Items.Add("완전히 종료", null, async (_, _) => await Quit());
        tray.ContextMenuStrip = menu;
        tray.DoubleClick += (_, _) => Dispatcher.Invoke(() => { Widget.Show(); ShowChat(); });
        SessionEnding += (_, _) => { _ = runtime.Stop(); };
        runtime.UnexpectedExit += () => Dispatcher.Invoke(() => {
            available = false;
            if (Widget != null) { Widget.Status.Text = "서버가 종료됐어요"; Widget.ChatButton.IsEnabled = false; }
        });
        try {
            await runtime.Start(Root, DataDirectory, e.Args.Contains("--smoke") || e.Args.Contains("--fake"));
            if (Exiting) return;
            Widget.Status.Text = "채팅을 준비하고 있어요…";
            chat = new ChatWindow(this);
            // WebView2 needs a realized WPF window before EnsureCoreWebView2Async.
            chat.ShowActivated = false;
            chat.Show();
            await chat.Initialize(runtime.Token);
            chat.Hide();
            available = true; Widget.ChatButton.IsEnabled = true; Widget.Status.Text = "여기 있어요";
            tray.Text = "NPC Chat · 실행 중";
            if (verifyReal) {
                CaptureWidget();
                await File.WriteAllTextAsync(Path.Combine(DataDirectory, "real-ready.json"), "{\"ready\":true,\"webview\":true}");
                await Quit();
            } else if (smoke) await Smoke();
        } catch (Exception ex) {
            if (smoke) {
                await File.WriteAllTextAsync(Path.Combine(DataDirectory, "smoke-error.txt"), ex.ToString());
                await Quit(1);
            } else if (!Exiting) {
                Widget.Status.Text = "시작하지 못했어요";
                MessageBox.Show("실행하지 못했습니다. 기존 서버가 켜져 있다면 먼저 종료해 주세요.\n\n" + ex.Message, "NPC Chat");
                await Quit(1);
            }
        }
    }

    public void ShowChat()
    {
        if (!available || chat == null) return;
        chat.Show(); chat.WindowState = WindowState.Normal; chat.Activate();
    }
    public async Task Quit(int code = 0)
    {
        if (Exiting) return;
        Exiting = true; available = false;
        if (Widget != null) { Widget.Status.Text = "모델과 서버 종료 중…"; Widget.ChatButton.IsEnabled = false; }
        await runtime.Stop();
        chat?.Browser.Dispose(); chat?.Close(); Widget?.Close();
        tray?.Dispose(); singleton?.Dispose(); Shutdown(code);
    }
    private async Task Smoke()
    {
        ShowChat();
        using var http = new HttpClient(new HttpClientHandler { UseProxy = false });
        if ((int)(await http.GetAsync(ChatWindow.Origin + "/api/live")).StatusCode != 403)
            throw new Exception("Unauthenticated request was accepted");
        await Task.Delay(1000); // Allow initial history restoration before measuring the new turn.
        var before = int.Parse(await chat!.Browser.CoreWebView2.ExecuteScriptAsync(
            "document.querySelectorAll('#chatThread .message-row.assistant:not(.typing-row)').length"));
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
    private void CaptureWidget()
    {
        var bitmap = new RenderTargetBitmap((int)Widget!.ActualWidth, (int)Widget.ActualHeight, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(Widget);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var output = File.Create(Path.Combine(DataDirectory, "widget.png")); encoder.Save(output);
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
            if (File.Exists(Path.Combine(directory.FullName, "scripts/desktop_runtime.py"))) return directory.FullName;
            directory = directory.Parent;
        }
        throw new InvalidOperationException("--root 옵션으로 프로젝트 위치를 지정해 주세요.");
    }
}
