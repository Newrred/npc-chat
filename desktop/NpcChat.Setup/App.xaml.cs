using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace NpcChat.Setup;

public partial class App : Application
{
    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        try {
            using var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("release.json") ?? throw new InvalidDataException("설치 payload가 설정되지 않은 개발 빌드입니다.");
            using var reader = new StreamReader(resource);
            var release = Installer.ReadRelease(await reader.ReadToEndAsync());
            var payloadRoot = Path.Combine(Path.GetDirectoryName(Environment.ProcessPath!)!, "payloads");
            var offline = Directory.Exists(payloadRoot);
            var http = new System.Net.Http.HttpClient(new System.Net.Http.HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
            Acquire acquire = offline ? (p, d, progress, ct) => LocalPayload.Copy(payloadRoot, p, d, progress, ct)
                : (p, d, progress, ct) => Installer.Download(http, p, d, progress, ct);
            var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "NpcChat");
            var selfTest = Array.IndexOf(e.Args, "--install-test");
            if (selfTest >= 0) {
                if (e.Args.Length <= selfTest + 1) throw new ArgumentException("검증 폴더가 필요합니다.");
                root = Path.GetFullPath(e.Args[selfTest + 1]);
                if (Directory.Exists(root)) throw new IOException("검증에는 비어 있는 새 경로를 지정하세요.");
                var result = await Installer.Install(release, root, acquire, new Progress<InstallProgress>(), CancellationToken.None);
                File.WriteAllText(Path.Combine(root, "install-test.json"), JsonSerializer.Serialize(new { success = true, id = release.Id, executable = File.Exists(Path.Combine(result, "NpcChat.Desktop.exe")) }));
                http.Dispose(); Shutdown(0); return;
            }
            var window = new Window { Title = "NPC Chat 설치 · 내부 테스트", Width = 510, Height = 390, ResizeMode = ResizeMode.NoResize, WindowStartupLocation = WindowStartupLocation.CenterScreen, Topmost = false, Background = new SolidColorBrush(Color.FromRgb(245,247,242)) };
            MainWindow = window;
            window.Closed += (_, _) => http.Dispose();
            var panel = new StackPanel { Margin = new Thickness(28) }; window.Content = panel;
            panel.Children.Add(new TextBlock { Text = "나만의 대화 공간", FontSize = 25, FontWeight = FontWeights.SemiBold, Margin = new Thickness(0,0,0,12) });
            panel.Children.Add(new TextBlock { Text = offline ? "앱과 모델이 포함된 오프라인 설치본입니다." : "앱과 모델을 다운로드하고 설치합니다.", FontSize = 14 });
            panel.Children.Add(new TextBlock { Text = "Windows x64 · NVIDIA GPU 권장 VRAM 8GB 이상\n기존 대화와 기억은 그대로 보존합니다.\n내부 테스트용 · 판매 배포 승인본이 아닙니다.", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0,12,0,12), Foreground = Brushes.DimGray });
            var status = new TextBlock { Text = "설치를 누르면 준비를 시작합니다.", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0,0,0,12) }; panel.Children.Add(status);
            var bar = new ProgressBar { Height = 6, Margin = new Thickness(0,0,0,18), Minimum = 0, Maximum = 100 }; panel.Children.Add(bar);
            var actions = new StackPanel { Orientation = Orientation.Horizontal }; panel.Children.Add(actions);
            var install = new Button { Content = "설치", Padding = new Thickness(22,8,22,8) }; actions.Children.Add(install);
            var cancel = new Button { Content = "취소", Padding = new Thickness(18,8,18,8), Margin = new Thickness(10,0,0,0), IsEnabled = false }; actions.Children.Add(cancel);
            CancellationTokenSource? source = null; bool running = false; string? installed = null;
            cancel.Click += (_, _) => source?.Cancel();
            window.Closing += (_, ev) => { if (running) { ev.Cancel = true; source?.Cancel(); status.Text = "현재 파일 작업을 안전하게 멈추고 있어요…"; } };
            install.Click += async (_, _) => {
                if (installed != null) {
                    Process.Start(new ProcessStartInfo(Path.Combine(installed, "NpcChat.Desktop.exe")) { UseShellExecute = true, WorkingDirectory = installed }); window.Close(); return;
                }
                if (running) return;
                running = true; install.IsEnabled = false; cancel.IsEnabled = true; source = new();
                try {
                    if (!Environment.Is64BitOperatingSystem) throw new InvalidOperationException("64비트 Windows가 필요합니다.");
                    var progress = new Progress<InstallProgress>(p => { status.Text = p.Stage; bar.IsIndeterminate = p.Total == 0; if (p.Total > 0) bar.Value = 100d * p.Done / p.Total; });
                    installed = await Task.Run(() => Installer.Install(release, root, acquire, progress, source.Token));
                    try { Shortcut(installed); status.Text = "설치 완료. 바탕화면에 NPC Chat 바로가기를 만들었습니다."; }
                    catch { status.Text = "설치는 완료됐지만 바로가기를 만들지 못했습니다. 아래 버튼으로 실행할 수 있어요."; }
                    install.Content = "앱 실행"; bar.IsIndeterminate = false; bar.Value = 100;
                } catch (OperationCanceledException) { status.Text = "설치를 멈췄습니다. 다시 시도하면 준비된 파일을 재사용합니다."; install.Content = "다시 시도"; }
                catch (Exception ex) { status.Text = "설치하지 못했어요. " + ex.Message; install.Content = "다시 시도"; }
                finally { running = false; install.IsEnabled = true; cancel.IsEnabled = false; bar.IsIndeterminate = false; source.Dispose(); source = null; }
            };
            window.Show();
            var preview = Array.IndexOf(e.Args, "--preview");
            if (preview >= 0 && e.Args.Length > preview + 1) {
                await Task.Delay(250); window.UpdateLayout();
                var bitmap = new System.Windows.Media.Imaging.RenderTargetBitmap((int)window.ActualWidth, (int)window.ActualHeight, 96, 96, PixelFormats.Pbgra32);
                bitmap.Render(window);
                var png = new System.Windows.Media.Imaging.PngBitmapEncoder(); png.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bitmap));
                using var file = new FileStream(e.Args[preview + 1], FileMode.CreateNew); png.Save(file);
                window.Close();
            }
        } catch (Exception ex) {
            if (!e.Args.Contains("--install-test")) MessageBox.Show(ex.Message, "NPC Chat 설치");
            Shutdown(1);
        }
    }
    static void Shortcut(string installed)
    {
        var type = Type.GetTypeFromProgID("WScript.Shell") ?? throw new InvalidOperationException();
        dynamic shell = Activator.CreateInstance(type)!;
        dynamic link = shell.CreateShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "NPC Chat.lnk"));
        link.TargetPath = Path.Combine(installed, "NpcChat.Desktop.exe"); link.WorkingDirectory = installed;
        link.Description = "NPC Chat"; link.Save();
    }
}
