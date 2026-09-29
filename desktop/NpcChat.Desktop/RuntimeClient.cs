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
    public event Action<string>? Progress;
    private bool stopping;
    private bool launched;
    private Task? stopTask;

    public Task Start(string root, string data, bool fake)
    {
        var packaged = File.Exists(Path.Combine(root, "desktop-package.json"));
        var python = packaged ? Path.Combine(root, "runtime", "python", "python.exe")
                              : Path.Combine(root, "venv", "Scripts", "python.exe");
        if (!File.Exists(python)) throw new InvalidOperationException("PYTHON_MISSING");
        if (!File.Exists(Path.Combine(root, "scripts", "desktop_runtime.py")))
            throw new InvalidOperationException("PACKAGE_INVALID");
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
            if (e.Data == null) { ready.TrySetException(new InvalidOperationException("PROCESS_EXITED")); return; }
            if (e.Data?.StartsWith("{\"desktop\"") != true) return;
            try {
                using var doc = JsonDocument.Parse(e.Data);
                var kind = doc.RootElement.GetProperty("desktop").GetString();
                if (kind == "ready") ready.TrySetResult();
                else if (kind == "progress") Progress?.Invoke(doc.RootElement.GetProperty("stage").GetString() ?? "");
                else if (kind == "error") ready.TrySetException(new InvalidOperationException(doc.RootElement.GetProperty("code").GetString()));
            } catch (Exception ex) when (ex is JsonException or System.Collections.Generic.KeyNotFoundException or InvalidOperationException) { }
        };
        process.ErrorDataReceived += (_, _) => { }; // Drain; service logs are local runtime files.
        process.Exited += (_, _) => {
            if (!stopping) UnexpectedExit?.Invoke();
        };
        launched = process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
        return ready.Task;
    }

    public Task Stop() => stopTask ??= StopCore();

    private async Task StopCore()
    {
        stopping = true;
        if (process == null) return;
        var target = process;
        if (!launched) { target.Dispose(); process = null; return; }
        if (!target.HasExited) {
            try { await target.StandardInput.WriteLineAsync("stop"); target.StandardInput.Close(); }
            catch (Exception ex) when (ex is IOException or InvalidOperationException) { }
        }
        // Supervisor owns cleanup; never kill processes merely by port or name.
        await target.WaitForExitAsync();
        target.Dispose(); process = null;
    }
}
