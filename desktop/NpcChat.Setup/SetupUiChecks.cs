using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace NpcChat.Setup;

internal static class SetupUiChecks
{
    public static async Task Run(Release release, string payloadRoot, Acquire local, Acquire online, string directory)
    {
        Directory.CreateDirectory(directory);
        Application.Current.ShutdownMode = ShutdownMode.OnExplicitShutdown;
        var mode = "cancel"; var launches = 0; Process? app = null;
        async Task Supply(Payload p, string destination, IProgress<InstallProgress> progress, CancellationToken ct)
        {
            if (mode == "cancel") { progress.Report(new("취소 검증 중")); await Task.Delay(Timeout.Infinite, ct); }
            if (mode == "failure") throw new IOException("합성 전송 중단");
            await local(p, destination, progress, ct);
        }
        void Launch(string installed)
        {
            launches++;
            if (launches == 1) throw new IOException("합성 실행 실패");
            app = Process.Start(new ProcessStartInfo(Path.Combine(installed, "NpcChat.Desktop.exe")) {
                UseShellExecute = false, WorkingDirectory = installed,
                Arguments = "--smoke-widget --no-topmost --data-dir \"" + Path.Combine(directory, "app-data") + "\""
            });
        }
        var link = Path.Combine(directory, "NPC Chat.lnk");
        var registryBase = @"Software\NpcChat\SetupTests\" + Guid.NewGuid().ToString("N");
        var scope = new WindowsScope(Path.Combine(directory,"Programs"),directory,Path.Combine(directory,"app-data"),registryBase);
        var window = new SetupWindow(release, payloadRoot, Supply, online, link, Launch, scope);
        Application.Current.MainWindow = window;
        window.Show(); await Task.Delay(200);
        void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
        Check(!window.Topmost, "Setup must not be topmost");
        window.MinimizeButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(window.WindowState == WindowState.Minimized, "Minimize failed");
        window.WindowState = WindowState.Normal;
        window.InstallPath.Text = Path.Combine(directory, "설치 대상");
        window.Capture(Path.Combine(directory, "01-options.png"));
        window.InstallPath.Text = "relative-path";
        await window.InstallAsync();
        Check(!window.Running && !window.Completed && window.StatusBox.Visibility == Visibility.Visible, "Invalid path accepted");
        window.Capture(Path.Combine(directory, "02-invalid-path.png"));
        window.InstallPath.Text = Path.Combine(directory, "설치 대상");
        window.PrimaryButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        await Task.Delay(250);
        window.Capture(Path.Combine(directory, "03-progress.png"));
        window.CloseButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        await window.Operation;
        Check(window.IsVisible && !window.Running && !window.Completed && window.Status.Text.Contains("취소"), "Close did not safely cancel");
        window.Capture(Path.Combine(directory, "04-cancelled.png"));
        mode = "failure";
        await window.InstallAsync();
        Check(!window.Completed && window.Status.Text.Contains("합성 전송 중단"), "Acquisition failure missing");
        window.Capture(Path.Combine(directory, "05-error.png"));
        mode = "real";
        window.PrimaryButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        await Task.Delay(500);
        window.Capture(Path.Combine(directory, "06-installing.png"));
        await window.Operation;
        Check(window.Completed && File.Exists(link), "Real install or shortcut failed: " + window.Status.Text);
        window.Capture(Path.Combine(directory, "07-complete.png"));
        window.PrimaryButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(window.IsVisible && window.Completed && window.Status.Text.Contains("앱을 열지 못"), "Launch failure lost completion state");
        window.Capture(Path.Combine(directory, "08-launch-error.png"));
        window.PrimaryButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(app != null && !window.IsVisible, "Finish did not launch installed app");
        await app!.WaitForExitAsync().WaitAsync(TimeSpan.FromMinutes(4));
        Check(app.ExitCode == 0, "Installed app smoke failed");
        var noLink = Path.Combine(directory, "must-not-create.lnk");
        var second = new SetupWindow(release, payloadRoot, local, online, noLink, _ => throw new Exception("Unchecked launch called"), scope);
        second.Show(); second.InstallPath.Text = Path.Combine(directory, "설치 대상"); second.DesktopShortcut.IsChecked = false;
        await second.InstallAsync();
        Check(second.Completed && !File.Exists(noLink), "Shortcut opt-out failed");
        second.LaunchAfter.IsChecked = false;
        second.PrimaryButton.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
        Check(!second.IsVisible, "Finish without launch failed");
        var installedRoot = Path.Combine(directory,"설치 대상");
        using (var registered = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(registryBase + "\\" + WindowsInstall.Identity(installedRoot)))
            Check(registered?.GetValue("DisplayName") as string == "NPC Chat", "Windows registration missing");
        Check(File.Exists(Path.Combine(WindowsInstall.MenuFolder(installedRoot,scope),"NPC Chat.lnk")),"Start menu missing");
        Check(File.Exists(Path.Combine(installedRoot,WindowsInstall.UninstallerName)),"Uninstaller missing");
        Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(registryBase,false);
        File.WriteAllText(Path.Combine(directory, "ui-test.json"), JsonSerializer.Serialize(new {
            passed = true, topmostOff = true, invalidPath = true, closeCancels = true, retry = true,
            shortcut = true, shortcutOptOut = true, launchFailureRecovery = true, launchOptOut = true,
            installedAppSmoke = app.ExitCode, release = release.Id
        }));
    }
}
