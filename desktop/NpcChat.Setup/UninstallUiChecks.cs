using System.IO;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Win32;

namespace NpcChat.Setup;

internal static class UninstallUiChecks
{
    internal static async Task Run(string output)
    {
        if (Directory.Exists(output)) throw new IOException("검증에는 새 폴더를 사용하세요.");
        Directory.CreateDirectory(output);
        var root = Path.Combine(output,"install"); var installed = Path.Combine(root,"releases","test");
        var scope = new WindowsScope(Path.Combine(output,"Programs"),Path.Combine(output,"Desktop"),Path.Combine(output,"UserData"),@"Software\NpcChat\SetupTests\"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(scope.Desktop); Directory.CreateDirectory(scope.Data);
        File.WriteAllText(Path.Combine(scope.Data,"synthetic-conversations"),"no real user data");
        string Hash(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
        var files = new[]{"NpcChat.Desktop.exe","models/model.gguf"};
        foreach(var name in files) {var p=Installer.SafePath(installed,name);Directory.CreateDirectory(Path.GetDirectoryName(p)!);File.WriteAllBytes(p,[1,2,3]);}
        var manifest=JsonSerializer.SerializeToUtf8Bytes(new {format=1,files=files.Select(n=>new{path=n,bytes=3,sha256=Hash([1,2,3])})});
        File.WriteAllBytes(Path.Combine(installed,"package-manifest.json"),manifest);
        var release=new Release(1,"test",6,"internal-test-only",Hash(manifest),[new Payload("app.zip",3,Hash([1,2,3])),new Payload("model.gguf",3,Hash([1,2,3]))]);
        WindowsInstall.Register(root,release,Environment.ProcessPath!,false,scope);
        bool confirm=false; int asks=0;
        var window=new UninstallWindow(root,release,scope,()=>{asks++;return confirm;});
        window.Show(); window.KeepData.IsChecked=false; window.KeepModel.IsChecked=false;
        await window.RemoveAsync();
        if(asks!=1 || !File.Exists(Path.Combine(installed,"NpcChat.Desktop.exe")) || !Directory.Exists(scope.Data)) throw new Exception("Declined data deletion changed files");
        confirm=true; await window.RemoveAsync();
        if(asks!=2 || Directory.Exists(scope.Data) || Directory.Exists(root)) throw new Exception("Confirmed deletion did not remove selected data/model/app");
        if(window.Topmost) throw new Exception("Uninstaller topmost enabled");
        window.Close(); Registry.CurrentUser.DeleteSubKeyTree(scope.RegistryBase,false);
        File.WriteAllText(Path.Combine(output,"ui-checks.json"),"{\"passed\":true,\"declinedDeletionPreserved\":true,\"confirmedDeletionRemoved\":true,\"topmostOff\":true}");
    }
}
