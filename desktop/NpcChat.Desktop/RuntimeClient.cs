using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading.Tasks;

namespace NpcChat.Desktop;

internal sealed class RuntimeClient
{
    public string Token { get; } = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
    private Process? process;
    private readonly TaskCompletionSource ready = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public event Action? UnexpectedExit;
    private bool stopping;

    public Task Start(string root, string data, bool fake)
    {
        var packaged = File.Exists(Path.Combine(root, "desktop-package.json"));
        var python = packaged ? Path.Combine(root, "runtime", "python", "python.exe")
                              : Path.Combine(root, "venv", "Scripts", "python.exe");
        if (!File.Exists(python)) throw new InvalidOperationException("프로젝트 Python 환경이 없습니다.");
        var info = new ProcessStartInfo(python) {
            WorkingDirectory = root, UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true
        };
        if (packaged) {
            // Keep OS identity/temp only; never inherit developer AI/proxy/Python settings.
            var allowed = new[] { "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA", "COMSPEC", "SYSTEMDRIVE",
                "PROGRAMFILES", "PROGRAMFILES(X86)", "COMMONPROGRAMFILES", "PROGRAMW6432", "COMMONPROGRAMW6432" };
            foreach (var name in info.Environment.Keys.ToArray())
                if (!allowed.Contains(name.ToUpperInvariant())) info.Environment.Remove(name);
            info.Environment["PATH"] = Environment.GetFolderPath(Environment.SpecialFolder.System);
            info.Environment["PYTHON_DOTENV_DISABLED"] = "1";
        }
        info.ArgumentList.Add(Path.Combine(root, "scripts", "desktop_runtime.py"));
        info.ArgumentList.Add("--data-dir"); info.ArgumentList.Add(data);
        if (fake) info.ArgumentList.Add("--fake");
        info.Environment["NPC_DESKTOP_TOKEN"] = Token;
        info.Environment["PYTHONIOENCODING"] = "utf-8";
        info.Environment["PYTHONUNBUFFERED"] = "1";
        process = new Process { StartInfo = info, EnableRaisingEvents = true };
        process.OutputDataReceived += (_, e) => {
            if (e.Data?.StartsWith("{\"desktop\"") != true) return;
            try {
                using var doc = JsonDocument.Parse(e.Data);
                if (doc.RootElement.GetProperty("desktop").GetString() == "ready") ready.TrySetResult();
                else ready.TrySetException(new InvalidOperationException(doc.RootElement.GetProperty("message").GetString()));
            } catch (JsonException) { }
        };
        process.ErrorDataReceived += (_, _) => { }; // Drain; service logs are local runtime files.
        process.Exited += (_, _) => {
            ready.TrySetException(new InvalidOperationException("모델 또는 서버를 시작하지 못했습니다. 다른 서버 실행 여부와 로컬 설정을 확인하세요."));
            if (!stopping) UnexpectedExit?.Invoke();
        };
        process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
        return ready.Task;
    }

    public async Task Stop()
    {
        stopping = true;
        if (process == null || process.HasExited) return;
        try { await process.StandardInput.WriteLineAsync("stop"); process.StandardInput.Close(); }
        catch (IOException) { }
        // Supervisor owns cleanup; never kill processes merely by port or name.
        await process.WaitForExitAsync();
        process.Dispose();
    }
}
