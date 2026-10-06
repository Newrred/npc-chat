using System.IO;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace NpcChat.Setup;

[SupportedOSPlatform("windows")]
public static class SetupShortcut
{
    public static void RemoveIfOwned(string linkPath, string target)
    {
        Installer.RejectLinks(linkPath);
        if (!File.Exists(linkPath)) return;
        var type = Type.GetTypeFromProgID("WScript.Shell") ?? throw new InvalidOperationException();
        object shell = Activator.CreateInstance(type)!; object? shortcut = null;
        try {
            shortcut = ((dynamic)shell).CreateShortcut(linkPath);
            if (string.Equals((string)((dynamic)shortcut).TargetPath, target, StringComparison.OrdinalIgnoreCase)) File.Delete(linkPath);
        } finally { if (shortcut != null) Marshal.FinalReleaseComObject(shortcut); Marshal.FinalReleaseComObject(shell); }
    }
    public static void Create(string installed, string linkPath)
    {
        var target = Path.GetFullPath(Path.Combine(installed, "NpcChat.Desktop.exe"));
        var type = Type.GetTypeFromProgID("WScript.Shell") ?? throw new InvalidOperationException();
        object shell = Activator.CreateInstance(type)!;
        object? shortcut = null;
        try {
            shortcut = ((dynamic)shell).CreateShortcut(linkPath);
            dynamic link = shortcut;
            if (File.Exists(linkPath)) {
                if (!string.Equals((string)link.TargetPath, target, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("같은 이름의 다른 바로가기가 있어 보존했습니다.");
                return; // Keep user customizations on an existing matching shortcut.
            }
            link.TargetPath = target;
            link.WorkingDirectory = installed;
            link.Description = "NPC Chat";
            link.IconLocation = target + ",0";
            link.Save();
        } finally {
            if (shortcut != null) Marshal.FinalReleaseComObject(shortcut);
            Marshal.FinalReleaseComObject(shell);
        }
    }
}
