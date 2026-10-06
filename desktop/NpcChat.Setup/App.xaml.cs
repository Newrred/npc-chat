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
            var removalChecks = Array.IndexOf(e.Args, "--uninstall-ui-checks");
            if (removalChecks >= 0) { ShutdownMode = ShutdownMode.OnExplicitShutdown; await UninstallUiChecks.Run(Path.GetFullPath(e.Args[removalChecks+1])); Shutdown(0); return; }
            var uninstall = Array.IndexOf(e.Args, "--uninstall");
            var worker = Array.IndexOf(e.Args, "--uninstall-worker");
            if (uninstall >= 0 || worker >= 0) {
                if (worker >= 0) Exit += (_, _) => UninstallHost.CleanupOnExit();
                var index = Math.Max(uninstall, worker);
                var uninstallRoot = Path.GetFullPath(e.Args[index + 1]);
                WindowsInstall.Read(uninstallRoot, release);
                var smokeIndex = Array.IndexOf(e.Args, "--uninstall-smoke");
                var smokeOutput = smokeIndex >= 0 ? Path.GetFullPath(e.Args[smokeIndex + 1]) : null;
                if (worker < 0) { UninstallHost.Detach(uninstallRoot, smokeOutput); Shutdown(0); return; }
                var removal = new UninstallWindow(uninstallRoot, release, smokeOutput == null ? null : WindowsScope.Current with {Data = Path.Combine(smokeOutput, "data")}); MainWindow = removal;
                if (smokeOutput != null) { ShutdownMode = ShutdownMode.OnExplicitShutdown; await removal.Smoke(smokeOutput); Shutdown(0); }
                else removal.Show();
                return;
            }
            var registerTest = Array.IndexOf(e.Args, "--register-test");
            if (registerTest >= 0) {
                var registerRoot = Path.GetFullPath(e.Args[registerTest + 1]);
                await Installer.VerifyInstalled(WindowsInstall.AppPath(registerRoot, release), CancellationToken.None, release.ManifestSha256);
                WindowsInstall.Register(registerRoot, release, Environment.ProcessPath!, false, WindowsScope.Current);
                Shutdown(0); return;
            }
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
            var uiTest = Array.IndexOf(e.Args, "--ui-test");
            var testDirectory = uiTest >= 0 && e.Args.Length > uiTest + 1 ? Path.GetFullPath(e.Args[uiTest + 1]) : null;
            if (uiTest >= 0 && (testDirectory == null || Directory.Exists(testDirectory))) throw new IOException("UI 검증에는 새 폴더를 지정하세요.");
            Acquire local = (p, d, progress, ct) => LocalPayload.Copy(payloadRoot, p, d, progress, ct);
            Acquire online = (p, d, progress, ct) => Installer.Download(http, p, d, progress, ct);
            var window = new SetupWindow(release, payloadRoot, local, online);
            MainWindow = window;
            window.Closed += (_, _) => http.Dispose();
            if (testDirectory != null) { await SetupUiChecks.Run(release, payloadRoot, local, online, testDirectory); http.Dispose(); Shutdown(0); return; }
            window.Show();
            var preview = Array.IndexOf(e.Args, "--preview");
            if (preview >= 0 && e.Args.Length > preview + 1) {
                await Task.Delay(250); window.UpdateLayout();
                window.Capture(e.Args[preview + 1]);
                window.Close();
            }
        } catch (Exception ex) {
            if (e.Args.Contains("--uninstall-ui-checks")) { var i = Array.IndexOf(e.Args, "--uninstall-ui-checks"); if (e.Args.Length > i + 1) { Directory.CreateDirectory(e.Args[i+1]); File.WriteAllText(Path.Combine(e.Args[i+1], "error.txt"), ex.ToString()); } }
            if (e.Args.Contains("--uninstall-smoke")) { var i = Array.IndexOf(e.Args, "--uninstall-smoke"); if (e.Args.Length > i + 1) { Directory.CreateDirectory(e.Args[i+1]); File.WriteAllText(Path.Combine(e.Args[i+1], "error.txt"), ex.ToString()); } }
            if (e.Args.Contains("--ui-test")) { var i = Array.IndexOf(e.Args, "--ui-test"); if (e.Args.Length > i + 1) { Directory.CreateDirectory(e.Args[i+1]); File.WriteAllText(Path.Combine(e.Args[i+1], "error.txt"), ex.ToString()); } }
            if (!e.Args.Contains("--install-test") && !e.Args.Contains("--ui-test") && !e.Args.Contains("--uninstall-smoke") && !e.Args.Contains("--uninstall-ui-checks")) MessageBox.Show(ex.Message, "NPC Chat 설치");
            Shutdown(1);
        }
    }
}
