using System.IO;
using System.Text.Json;

namespace NpcChat.Setup;

public static class SetupOptions
{
    public static string ValidateRoot(string text, Release release, string payloadRoot, string userData)
    {
        if (string.IsNullOrWhiteSpace(text) || !Path.IsPathFullyQualified(text.Trim()))
            throw new IOException("드라이브부터 시작하는 전체 설치 경로를 입력해 주세요.");
        var root = Path.GetFullPath(text.Trim()).TrimEnd(Path.DirectorySeparatorChar);
        if (root.Length < 4 || root.StartsWith("\\\\") || root.IndexOf(':', 2) >= 0)
            throw new IOException("로컬 드라이브의 전용 폴더를 선택해 주세요.");
        Installer.RejectLinks(root);
        foreach (var protectedPath in new[] {userData, payloadRoot, Environment.GetFolderPath(Environment.SpecialFolder.Windows)}) {
            if (string.IsNullOrEmpty(protectedPath)) continue;
            if (Contains(root, protectedPath) || Contains(protectedPath, root))
                throw new IOException("개인 데이터·설치 원본·Windows 폴더와 겹치지 않는 전용 폴더를 선택해 주세요.");
        }
        if (File.Exists(root)) throw new IOException("파일이 아닌 폴더를 선택해 주세요.");
        if (Directory.Exists(root) && Directory.EnumerateFileSystemEntries(root).Any()) {
            var known = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {"cache", "staging", "releases", "current.json", "install.lock", "install-state.json", "NPCChatUninstall.exe", "retained-models"};
            if (Directory.EnumerateFileSystemEntries(root).Any(p => !known.Contains(Path.GetFileName(p))))
                throw new IOException("다른 파일이 있는 폴더입니다. NPC Chat 전용 새 폴더를 선택해 주세요.");
            var current = Path.Combine(root, "current.json");
            if (File.Exists(current) && JsonSerializer.Deserialize<string>(File.ReadAllText(current)) != release.Id)
                throw new IOException("다른 버전이 설치되어 있어요. 이번 설치본은 업데이트를 지원하지 않습니다. 새 폴더를 선택해 주세요.");
        }
        return root;
    }
    private static bool Contains(string parent, string child)
    {
        parent = Path.GetFullPath(parent).TrimEnd(Path.DirectorySeparatorChar);
        child = Path.GetFullPath(child).TrimEnd(Path.DirectorySeparatorChar);
        return parent.Equals(child, StringComparison.OrdinalIgnoreCase)
            || child.StartsWith(parent + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }
    public static bool CanDownload(Release release) => release.Payloads.All(p => p.Url != null);
    public static bool HasLocal(Release release, string root) => release.Payloads.All(p => {
        var file = Path.Combine(root, p.Name);
        return File.Exists(file) && new FileInfo(file).Length == p.Bytes;
    });
    public static string Size(long bytes) => $"{bytes / 1_000_000_000d:0.00} GB";
}
