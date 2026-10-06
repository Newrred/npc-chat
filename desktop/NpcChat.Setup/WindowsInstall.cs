using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Runtime.Versioning;
using Microsoft.Win32;

namespace NpcChat.Setup;

public record InstallOwnership(int Format, string Root, string Release, string ManifestHash, string UninstallerHash, bool Desktop);
public record WindowsScope(string Programs, string Desktop, string Data, string RegistryBase)
{
    public static WindowsScope Current => new(
        Environment.GetFolderPath(Environment.SpecialFolder.Programs),
        Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "NpcChatDesktop"),
        @"Software\Microsoft\Windows\CurrentVersion\Uninstall");
}

[SupportedOSPlatform("windows")]
public static class WindowsInstall
{
    public const string StateName = "install-state.json";
    public const string UninstallerName = "NPCChatUninstall.exe";
    public static string Identity(string root) => "NpcChat-" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(root).TrimEnd('\\').ToUpperInvariant())))[..16];
    public static string MenuFolder(string root, WindowsScope scope) => Path.Combine(scope.Programs, "NPC Chat (" + Identity(root)[8..] + ")");
    public static string AppPath(string root, Release release) => Installer.SafePath(root, "releases/" + release.Id);
    public static string RetainedModel(string root, Release release) => Installer.SafePath(root, "retained-models/" + release.Payloads.Single(p => p.Name == "model.gguf").Sha256 + ".gguf");
    static string Hash(string file) { using var s = File.OpenRead(file); return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant(); }

    public static void Register(string root, Release release, string setupExe, bool desktop, WindowsScope scope)
    {
        root = Path.GetFullPath(root).TrimEnd('\\');
        Installer.RejectLinks(root);
        var statePath = Installer.SafePath(root, StateName);
        var target = Installer.SafePath(root, UninstallerName);
        var installed = AppPath(root, release);
        if (File.Exists(statePath)) desktop |= Read(root, release, false).Desktop;
        else if (File.Exists(target)) throw new IOException("기존 제거 파일이 있어 덮어쓰지 않았습니다.");
        // A trusted setup can retry partial registration; uninstall remains strict.
        var ownership = new InstallOwnership(1, root, release.Id, release.ManifestSha256, Hash(setupExe), desktop);
        var temp = Installer.SafePath(root, "install-state.json.tmp");
        File.WriteAllText(temp, JsonSerializer.Serialize(ownership));
        File.Move(temp, statePath, true);
        File.Copy(setupExe, target, true);
        var menu = MenuFolder(root, scope); Installer.RejectLinks(menu); Directory.CreateDirectory(menu);
        SetupShortcut.Create(installed, Path.Combine(menu, "NPC Chat.lnk"));
        using var key = Registry.CurrentUser.CreateSubKey(scope.RegistryBase + "\\" + Identity(root));
        var previous = key.GetValue("InstallLocation") as string;
        if (previous != null && !string.Equals(previous, root, StringComparison.OrdinalIgnoreCase)) throw new IOException("다른 설치 등록을 보존했습니다.");
        key.SetValue("DisplayName", "NPC Chat"); key.SetValue("DisplayVersion", release.Id);
        key.SetValue("Publisher", "NPC Chat"); key.SetValue("InstallLocation", root);
        key.SetValue("DisplayIcon", Path.Combine(installed, "NpcChat.Desktop.exe") + ",0");
        key.SetValue("UninstallString", "\"" + target + "\" --uninstall \"" + root + "\"");
        key.SetValue("NoModify", 1, RegistryValueKind.DWord); key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
        key.SetValue("EstimatedSize", (int)Math.Min(int.MaxValue, (release.ExpandedBytes + release.Payloads.Single(p => p.Name == "model.gguf").Bytes + new FileInfo(target).Length) / 1024), RegistryValueKind.DWord);
    }

    public static InstallOwnership Read(string root, Release release, bool verifyUninstaller = true)
    {
        root = Path.GetFullPath(root).TrimEnd('\\');
        if (root.Length < 4 || root.StartsWith("\\\\")) throw new IOException("잘못된 설치 위치입니다.");
        var state = JsonSerializer.Deserialize<InstallOwnership>(File.ReadAllText(Installer.SafePath(root, StateName)), Installer.Json)
            ?? throw new InvalidDataException("설치 소유 정보가 없습니다.");
        if (state.Format != 1 || !string.Equals(state.Root, root, StringComparison.OrdinalIgnoreCase)
            || state.Release != release.Id || state.ManifestHash != release.ManifestSha256)
            throw new InvalidDataException("이 제거 프로그램의 설치 정보와 일치하지 않습니다.");
        var exe = Installer.SafePath(root, UninstallerName);
        if (verifyUninstaller && File.Exists(exe) && Hash(exe) != state.UninstallerHash) throw new InvalidDataException("제거 프로그램이 변경되었습니다.");
        return state;
    }

    public static void Remove(string root, Release release, bool keepData, bool keepModel, WindowsScope scope)
    {
        root = Path.GetFullPath(root).TrimEnd('\\');
        var state = Read(root, release);
        if (Overlaps(root, scope.Data) || Overlaps(root, Environment.GetFolderPath(Environment.SpecialFolder.Windows)))
            throw new IOException("설치 폴더와 보호 경로가 겹칩니다.");
        // Same mutex name as the desktop app: prevent its normal startup throughout removal.
        var dataKey = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(scope.Data).ToUpperInvariant())));
        using var appGuard = new Mutex(true, "Local\\NpcChatDesktop-" + dataKey, out var first);
        if (!first) throw new IOException("NPC Chat을 트레이에서 완전히 종료한 후 다시 시도해 주세요.");
        try {
            using var installGuard = new FileStream(Installer.SafePath(root, "install.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            var installed = AppPath(root, release);
            var manifest = Installer.SafePath(installed, "package-manifest.json");
            if (Hash(manifest) != release.ManifestSha256) throw new InvalidDataException("설치 목록이 변경되어 제거를 중단했습니다.");
            using var doc = JsonDocument.Parse(File.ReadAllText(manifest));
            var files = doc.RootElement.GetProperty("files").EnumerateArray().Select(f => Installer.SafePath(installed, f.GetProperty("path").GetString()!)).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            // Python creates bytecode beside owned sources after first run. Only recognize
            // the exact source stem + CPython cache naming convention, not arbitrary files.
            foreach (var source in files.Where(p => p.EndsWith(".py", StringComparison.OrdinalIgnoreCase)).ToArray()) {
                var cache = Path.Combine(Path.GetDirectoryName(source)!, "__pycache__");
                Installer.RejectLinks(cache);
                if (!Directory.Exists(cache)) continue;
                var pattern = "^" + System.Text.RegularExpressions.Regex.Escape(Path.GetFileNameWithoutExtension(source)) + @"\.cpython-[0-9]+(?:\.opt-[12])?\.pyc$";
                foreach (var generated in Directory.EnumerateFiles(cache))
                    if (System.Text.RegularExpressions.Regex.IsMatch(Path.GetFileName(generated), pattern))
                        files.Add(Installer.SafePath(installed, Path.GetRelativePath(installed, generated).Replace('\\','/')));
            }
            var model = Installer.SafePath(installed, "models/model.gguf");
            if (!files.Contains(model, StringComparer.OrdinalIgnoreCase)) throw new InvalidDataException("모델 소유 정보가 없습니다.");
            var retained = RetainedModel(root, release);
            if (File.Exists(retained) && Hash(retained) != release.Payloads.Single(p => p.Name == "model.gguf").Sha256)
                throw new IOException("보존 모델 경로에 다른 파일이 있어 중단했습니다.");
            if (!keepModel && File.Exists(retained)) files.Add(retained);
            TreeFiles(root); // Reject junctions even in otherwise unowned directories before mutation.
            Installer.RejectLinks(MenuFolder(root, scope));
            Installer.RejectLinks(Path.Combine(scope.Desktop, "NPC Chat.lnk"));
            using (var registered = Registry.CurrentUser.OpenSubKey(scope.RegistryBase + "\\" + Identity(root)))
                if (registered != null && !string.Equals(registered.GetValue("InstallLocation") as string, root, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("다른 설치 등록이므로 보존했습니다.");
            var dataFiles = keepData ? new List<string>() : TreeFiles(scope.Data);
            var controls = new[] {Installer.SafePath(root, UninstallerName), Installer.SafePath(root, "current.json"), manifest};
            foreach (var file in files.Concat(dataFiles).Concat(controls).Where(File.Exists)) {
                using var check = new FileStream(file, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            }
            // All paths, links and locks are checked before deleting the first file.
            if (keepModel && File.Exists(model) && !File.Exists(retained)) { Directory.CreateDirectory(Path.GetDirectoryName(retained)!); File.Move(model, retained); }
            foreach (var file in files) if (File.Exists(file)) File.Delete(file);
            foreach (var file in dataFiles) File.Delete(file);
            if (!keepData) Prune(scope.Data);
            var exe = Path.Combine(installed, "NpcChat.Desktop.exe");
            var menu = MenuFolder(root, scope);
            SetupShortcut.RemoveIfOwned(Path.Combine(menu, "NPC Chat.lnk"), exe);
            if (state.Desktop) SetupShortcut.RemoveIfOwned(Path.Combine(scope.Desktop, "NPC Chat.lnk"), exe);
            RemoveEmpty(menu);
            using (var key = Registry.CurrentUser.OpenSubKey(scope.RegistryBase + "\\" + Identity(root))) {
                if (key != null && !string.Equals(key.GetValue("InstallLocation") as string, root, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("다른 설치 등록이므로 보존했습니다.");
            }
            Registry.CurrentUser.DeleteSubKeyTree(scope.RegistryBase + "\\" + Identity(root), false);
            foreach (var file in controls) if (File.Exists(file)) File.Delete(file);
            File.Delete(Installer.SafePath(root, StateName));
            foreach (var file in files.Concat(controls)) {
                for (var dir = Path.GetDirectoryName(file); dir != null && !dir.Equals(root, StringComparison.OrdinalIgnoreCase); dir = Path.GetDirectoryName(dir)) RemoveEmpty(dir);
            }
        } finally { appGuard.ReleaseMutex(); }
        File.Delete(Installer.SafePath(root, "install.lock"));
        foreach (var name in new[] {"cache", "staging", "releases", "retained-models"}) RemoveEmpty(Installer.SafePath(root, name));
        RemoveEmpty(root); // Unknown files and their directories remain.
    }

    static bool Overlaps(string a, string b) {
        a = Path.GetFullPath(a).TrimEnd('\\'); b = Path.GetFullPath(b).TrimEnd('\\');
        return a.Equals(b, StringComparison.OrdinalIgnoreCase) || a.StartsWith(b + "\\", StringComparison.OrdinalIgnoreCase) || b.StartsWith(a + "\\", StringComparison.OrdinalIgnoreCase);
    }
    static List<string> TreeFiles(string root) {
        Installer.RejectLinks(root); var files = new List<string>();
        if (!Directory.Exists(root)) return files;
        foreach (var p in Directory.EnumerateFileSystemEntries(root)) { Installer.RejectLinks(p); if (Directory.Exists(p)) files.AddRange(TreeFiles(p)); else files.Add(p); }
        return files;
    }
    static void Prune(string root) {
        Installer.RejectLinks(root); if (!Directory.Exists(root)) return;
        foreach (var p in Directory.EnumerateDirectories(root)) { Installer.RejectLinks(p); Prune(p); }
        if (!Directory.EnumerateFileSystemEntries(root).Any()) Directory.Delete(root, false);
    }
    static void RemoveEmpty(string path) { Installer.RejectLinks(path); if (Directory.Exists(path) && !Directory.EnumerateFileSystemEntries(path).Any()) Directory.Delete(path, false); }
}
