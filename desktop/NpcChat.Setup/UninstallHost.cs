using System.Diagnostics;
using System.IO;
using System.Text;

namespace NpcChat.Setup;

internal static class UninstallHost
{
    public static void Detach(string root, string? smoke)
    {
        var folder = Path.Combine(Path.GetTempPath(), "NpcChat-remove-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        var exe = Path.Combine(folder, WindowsInstall.UninstallerName);
        File.Copy(Environment.ProcessPath!, exe);
        var start = new ProcessStartInfo(exe) {UseShellExecute=false, WorkingDirectory=folder};
        start.ArgumentList.Add("--uninstall-worker"); start.ArgumentList.Add(root);
        if (smoke != null) { start.ArgumentList.Add("--uninstall-smoke"); start.ArgumentList.Add(smoke); }
        _ = Process.Start(start) ?? throw new IOException("제거 화면을 열지 못했습니다.");
    }
    public static void CleanupOnExit()
    {
        var exe = Path.GetFullPath(Environment.ProcessPath!); var dir = Path.GetDirectoryName(exe)!;
        var tempRoot = Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\') + "\\";
        if (!dir.StartsWith(tempRoot, StringComparison.OrdinalIgnoreCase)
            || !System.Text.RegularExpressions.Regex.IsMatch(Path.GetFileName(dir), "^NpcChat-remove-[a-f0-9]{32}$")
            || Path.GetFileName(exe) != WindowsInstall.UninstallerName) return;
        // The helper deletes exactly the copied EXE and its empty temp directory, never recursively.
        string Quote(string s) => "'" + s.Replace("'", "''") + "'";
        var script = "$ErrorActionPreference='Stop'; Wait-Process -Id " + Environment.ProcessId
            + " -ErrorAction SilentlyContinue; Remove-Item -LiteralPath " + Quote(exe)
            + "; [System.IO.Directory]::Delete(" + Quote(dir) + ",$false)";
        var start = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe")) {UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,WorkingDirectory=Path.GetTempPath()};
        start.ArgumentList.Add("-NoProfile"); start.ArgumentList.Add("-NonInteractive"); start.ArgumentList.Add("-EncodedCommand");
        start.ArgumentList.Add(Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
        Process.Start(start);
    }
}
