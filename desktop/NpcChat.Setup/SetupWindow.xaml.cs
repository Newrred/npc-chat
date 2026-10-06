using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;

namespace NpcChat.Setup;

public partial class SetupWindow : Window
{
    private readonly Release release;
    private readonly string payloadRoot;
    private readonly Acquire local, online;
    private readonly string shortcutPath;
    private readonly Action<string> launch;
    private readonly WindowsScope? registrationScope;
    private CancellationTokenSource? cancellation;
    private string? installed;
    internal Task Operation { get; private set; } = Task.CompletedTask;
    internal bool Running => cancellation != null;
    internal bool Completed => installed != null;

    public SetupWindow(Release release, string payloadRoot, Acquire local, Acquire online,
                       string? testShortcut = null, Action<string>? testLaunch = null, WindowsScope? testScope = null)
    {
        InitializeComponent();
        this.release = release; this.payloadRoot = payloadRoot; this.local = local; this.online = online;
        registrationScope = testScope ?? (testShortcut == null ? WindowsScope.Current : null);
        shortcutPath = testShortcut ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "NPC Chat.lnk");
        launch = testLaunch ?? (path => Process.Start(new ProcessStartInfo(Path.Combine(path, "NpcChat.Desktop.exe")) {UseShellExecute = true, WorkingDirectory = path}));
        InstallPath.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "NpcChat");
        LocalSource.IsEnabled = SetupOptions.HasLocal(release, payloadRoot);
        OnlineSource.IsEnabled = SetupOptions.CanDownload(release);
        LocalSource.IsChecked = LocalSource.IsEnabled;
        OnlineSource.IsChecked = !LocalSource.IsEnabled && OnlineSource.IsEnabled;
        PrimaryButton.IsEnabled = LocalSource.IsEnabled || OnlineSource.IsEnabled;
        SourceNote.Text = !PrimaryButton.IsEnabled ? "설치 파일이 없습니다. ZIP을 전부 풀어 payloads 폴더와 함께 실행해 주세요."
            : !OnlineSource.IsEnabled ? "이 동봉판에는 온라인 다운로드 주소가 설정되어 있지 않습니다."
            : !LocalSource.IsEnabled ? "동봉 파일이 없어 인터넷으로 설치 파일을 받습니다." : "원하는 파일 준비 방식을 선택해 주세요.";
        SpaceNote.Text = $"설치 후 약 {SetupOptions.Size(release.ExpandedBytes + release.Payloads.Single(p => p.Name == "model.gguf").Bytes)} · 임시 파일 포함 필요 공간은 설치 시작 시 확인합니다.";
        InstallPath.TextChanged += (_, _) => UpdateSpace();
        UpdateSpace();
        Closing += ClosingSetup;
        Height = Math.Min(Height, SystemParameters.WorkArea.Height);
        Width = Math.Min(Width, SystemParameters.WorkArea.Width);
    }
    private void Minimize(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    private void UpdateSpace()
    {
        try {
            var root = SetupOptions.ValidateRoot(InstallPath.Text, release, payloadRoot,
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NpcChatDesktop"));
            SpaceNote.Text = $"임시 파일 포함 필요 {SetupOptions.Size(Installer.RequiredSpace(release, root))} · 드라이브 여유 {SetupOptions.Size(new DriveInfo(Path.GetPathRoot(root)!).AvailableFreeSpace)}";
        } catch { SpaceNote.Text = "설치 시작 전에 경로와 필요한 저장 공간을 확인합니다."; }
    }
    private void CloseSetup(object sender, RoutedEventArgs e) => Close();
    private void ClosingSetup(object? sender, CancelEventArgs e)
    {
        if (Running) { e.Cancel = true; RequestCancel(); }
    }
    private void Browse(object sender, RoutedEventArgs e)
    {
        var picker = new OpenFolderDialog {Title = "NPC Chat을 설치할 전용 폴더 선택", Multiselect = false};
        if (Directory.Exists(InstallPath.Text)) picker.InitialDirectory = InstallPath.Text;
        if (picker.ShowDialog(this) == true) InstallPath.Text = picker.FolderName;
    }
    private void Cancel(object sender, RoutedEventArgs e) { if (Running) RequestCancel(); else Close(); }
    private void RequestCancel()
    {
        cancellation?.Cancel(); CancelButton.IsEnabled = false;
        ShowStatus("현재 파일 작업을 안전하게 멈추고 있어요…");
    }
    private void ShowStatus(string text)
    {
        Status.Text = text; StatusBox.Visibility = Visibility.Visible;
    }
    private void Primary(object sender, RoutedEventArgs e)
    {
        if (Running) return;
        if (installed != null) {
            try { if (LaunchAfter.IsChecked == true) launch(installed); Close(); }
            catch (Exception ex) { ShowStatus("설치는 완료됐지만 앱을 열지 못했어요. 다시 시도하거나 설치 폴더에서 실행해 주세요. " + ex.Message); }
            return;
        }
        Operation = InstallAsync();
    }
    internal async Task InstallAsync()
    {
        if (Running || Completed) return;
        string root;
        try {
            if (!Environment.Is64BitOperatingSystem) throw new IOException("64비트 Windows가 필요합니다.");
            root = SetupOptions.ValidateRoot(InstallPath.Text, release, payloadRoot,
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NpcChatDesktop"));
            if (LocalSource.IsChecked != true && OnlineSource.IsChecked != true) throw new IOException("사용 가능한 설치 파일을 선택해 주세요.");
            var needed = Installer.RequiredSpace(release, root);
            var free = new DriveInfo(Path.GetPathRoot(root)!).AvailableFreeSpace;
            if (free < needed) throw new IOException($"저장 공간이 부족합니다. 필요 {SetupOptions.Size(needed)} / 여유 {SetupOptions.Size(free)}");
            SpaceNote.Text = $"필요 {SetupOptions.Size(needed)} / 여유 {SetupOptions.Size(free)}";
        } catch (Exception ex) { ShowStatus(ex.Message); return; }
        cancellation = new(); var source = cancellation;
        OptionsPanel.Visibility = Visibility.Collapsed; ProgressPanel.Visibility = Visibility.Visible;
        StatusBox.Visibility = Visibility.Collapsed; PrimaryButton.IsEnabled = false; CancelButton.Content = "설치 취소";
        Heading.Text = "대화할 준비를 하고 있어요"; Steps.Text = "01  설정 완료       →       02  파일 설치 중       →       03  완료";
        Bar.IsIndeterminate = true; Phase.Text = "설치 준비 중"; ProgressDetail.Text = SpaceNote.Text;
        var warnings = new List<string>();
        var progress = new Progress<InstallProgress>(p => {
            if (cancellation != source || source.IsCancellationRequested) return;
            Phase.Text = p.Stage;
            if (p.Stage.Contains("정리하지 못")) warnings.Add(p.Stage);
            Bar.IsIndeterminate = p.Total <= 0;
            if (p.Total > 0) { Bar.Value = Math.Clamp(100d * p.Done / p.Total, 0, 100); ProgressDetail.Text = $"현재 파일 {Bar.Value:0}% · {SetupOptions.Size(p.Done)} / {SetupOptions.Size(p.Total)}"; }
            else ProgressDetail.Text = "파일 크기와 무결성을 확인하고 있어요.";
        });
        var acquire = LocalSource.IsChecked == true ? local : online;
        try {
            installed = await Task.Run(() => Installer.Install(release, root, acquire, progress, source.Token));
            if (registrationScope != null) {
                try { WindowsInstall.Register(root, release, Environment.ProcessPath!, DesktopShortcut.IsChecked == true, registrationScope); }
                catch (Exception ex) { installed = null; throw new IOException("앱 파일은 설치됐지만 Windows 등록에 실패했어요. 다시 시도해 주세요. " + ex.Message, ex); }
            }
            if (DesktopShortcut.IsChecked == true) {
                try { SetupShortcut.Create(installed, shortcutPath); }
                catch (Exception ex) { warnings.Add("바로가기를 만들지 못했어요. " + ex.Message); }
            }
            ProgressPanel.Visibility = Visibility.Collapsed; DonePanel.Visibility = Visibility.Visible;
            Heading.Text = "NPC Chat 설치 완료"; Subtitle.Text = "이제 캐릭터와 첫 이야기를 시작해 보세요.";
            Steps.Text = "01  설정 완료       →       02  설치 완료       →       03  실행 준비";
            DonePath.Text = $"설치 위치\n{installed}\n\n" + (DesktopShortcut.IsChecked == true && warnings.Count == 0 ? "바탕화면 바로가기를 만들었어요." : "아래 완료 버튼으로 앱을 실행할 수 있어요.");
            if (registrationScope != null) DonePath.Text += "\n시작 메뉴와 Windows 설치된 앱에 등록했어요.";
            PrimaryButton.Content = "완료";
            if (warnings.Count > 0) ShowStatus(string.Join("\n", warnings));
        } catch (OperationCanceledException) { ReturnToOptions("설치를 취소했어요. 다시 시작하면 준비된 파일을 재사용합니다."); }
        catch (Exception ex) { ReturnToOptions("설치하지 못했어요. " + ex.Message); }
        finally {
            cancellation = null; source.Dispose(); PrimaryButton.IsEnabled = true; CancelButton.IsEnabled = true;
            CancelButton.Content = "닫기"; Bar.IsIndeterminate = false;
        }
    }
    private void ReturnToOptions(string message)
    {
        OptionsPanel.Visibility = Visibility.Visible; ProgressPanel.Visibility = Visibility.Collapsed;
        Heading.Text = "설정을 확인하고 다시 시작해요"; PrimaryButton.Content = "다시 시도";
        Steps.Text = "01  설치 설정       →       02  파일 설치       →       03  완료"; ShowStatus(message);
    }
    private void OpenFolder(object sender, RoutedEventArgs e)
    {
        try { if (installed != null) Process.Start(new ProcessStartInfo(installed) {UseShellExecute = true}); }
        catch (Exception ex) { ShowStatus("폴더를 열지 못했어요. " + ex.Message); }
    }
    internal void Capture(string path)
    {
        UpdateLayout();
        var bitmap = new RenderTargetBitmap((int)ActualWidth, (int)ActualHeight, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(this); var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(bitmap));
        using var file = new FileStream(path, FileMode.CreateNew); png.Save(file);
    }
}
