using System.IO.Compression;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using NpcChat.Setup;

var checks = 0;
void Check(bool b, string name) { if (!b) throw new Exception(name); checks++; }
async Task Reject(Func<Task> action, string name) { try { await action(); } catch (Exception e) when (e is IOException or InvalidDataException or InvalidOperationException or OperationCanceledException) { checks++; return; } throw new Exception(name); }
string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
var folder = Path.Combine(Path.GetTempPath(), "npc-setup-checks-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(folder);
var fixture = Path.Combine(folder,"fixture"); Directory.CreateDirectory(fixture);
var names = new[] { "NpcChat.Desktop.exe", "desktop-package.json", "runtime/python/python.exe", "runtime/llama/llama-server.exe", "runtime/webview2/msedgewebview2.exe", "models/model.gguf" };
var files = names.Select(n => new {path=n,bytes=3,sha256=Hash(new byte[]{1,2,3})}).ToArray();
foreach (var n in names) { var p=Path.Combine(fixture,n); Directory.CreateDirectory(Path.GetDirectoryName(p)!); File.WriteAllBytes(p,[1,2,3]); }
var manifest=JsonSerializer.Serialize(new {format=1,files}); File.WriteAllText(Path.Combine(fixture,"package-manifest.json"),manifest);
var zip=Path.Combine(folder,"app.zip");
using (var a=ZipFile.Open(zip,ZipArchiveMode.Create)) foreach(var p in Directory.GetFiles(fixture,"*",SearchOption.AllDirectories).Where(p=>!p.EndsWith("model.gguf"))) a.CreateEntryFromFile(p,Path.GetRelativePath(fixture,p).Replace('\\','/'));
var payloads=new[]{new Payload("app.zip",new FileInfo(zip).Length,Hash(File.ReadAllBytes(zip))),new Payload("model.gguf",3,Hash([1,2,3]))};
var release=new Release(1,"1.4.0-test",100000,"internal-test-only",Hash(Encoding.UTF8.GetBytes(manifest)),payloads);
var progress=new Progress<InstallProgress>();
Acquire acquire=(p,d,_,_)=>{ File.Copy(p.Name=="app.zip"?zip:Path.Combine(fixture,"models/model.gguf"),d,true);return Task.CompletedTask;};
var root=Path.Combine(folder,"installed");
var installed=await Installer.Install(release,root,acquire,progress,CancellationToken.None);
Check(File.Exists(Path.Combine(root,"current.json")),"activation");
Check(await Installer.Install(release,root,(_,_,_,_)=>throw new Exception("reacquired"),progress,CancellationToken.None)==installed,"idempotent retry");
File.Delete(Path.Combine(root,"current.json"));
Check(await Installer.Install(release,root,acquire,progress,CancellationToken.None)==installed,"recover rename before pointer");
await Reject(()=>Installer.Install(release with{Id="different"},root,acquire,progress,CancellationToken.None),"reject unsupported update");
foreach(var path in new[]{"../outside","C:/outside","a\\b","/absolute","CON.txt","a./x","a//x","file:stream"})
 await Reject(()=>Task.FromResult(Installer.SafePath(root,path)),"bad path "+path);
File.AppendAllText(Path.Combine(installed,"package-manifest.json")," ");
await Reject(()=>Installer.VerifyInstalled(installed,CancellationToken.None,release.ManifestSha256),"manifest tampering");
var canceledRoot=Path.Combine(folder,"canceled");
await Reject(()=>Installer.Install(release,canceledRoot,(_,_,_,_)=>throw new OperationCanceledException(),progress,CancellationToken.None),"cancellation");
Check(!File.Exists(Path.Combine(canceledRoot,"current.json")),"cancel keeps inactive");
Check(Directory.Exists(await Installer.Install(release,canceledRoot,acquire,progress,CancellationToken.None)),"resume installation");
var corruptRoot=Path.Combine(folder,"corrupt");
await Reject(()=>Installer.Install(release,corruptRoot,(p,d,_,_)=>File.WriteAllTextAsync(d,"bad"),progress,CancellationToken.None),"bad payload hash");
Check(!File.Exists(Path.Combine(corruptRoot,"current.json")),"bad hash keeps inactive");
using(var a=ZipFile.Open(Path.Combine(folder,"evil.zip"),ZipArchiveMode.Create)){using var w=new StreamWriter(a.CreateEntry("../escape").Open());w.Write("no");}
var evil=File.ReadAllBytes(Path.Combine(folder,"evil.zip"));
var evilRelease=release with{Payloads=[new Payload("app.zip",evil.Length,Hash(evil)),payloads[1]]};
await Reject(()=>Installer.Install(evilRelease,Path.Combine(folder,"evil"),(p,d,_,_)=>File.WriteAllBytesAsync(d,p.Name=="app.zip"?evil:new byte[]{1,2,3}),progress,CancellationToken.None),"zip traversal");
var bytes=Encoding.UTF8.GetBytes("download fixture"); var download=new Payload("model.gguf",bytes.Length,Hash(bytes),"https://example.invalid/model");
var part=Path.Combine(folder,"download.part");File.WriteAllBytes(part,bytes[..3]);
using(var client=new HttpClient(new FakeHandler(req=>{
 Check(req.Headers.Range?.Ranges.Single().From==3,"resume range sent");
 var response=new HttpResponseMessage(HttpStatusCode.PartialContent){RequestMessage=req,Content=new ByteArrayContent(bytes[3..])};
 response.Content.Headers.ContentRange=new ContentRangeHeaderValue(3,bytes.Length-1,bytes.Length);return response;
}))) await Installer.Download(client,download,part,progress,CancellationToken.None);
Check(await Installer.Matches(part,download,CancellationToken.None),"206 resumed hash");
File.WriteAllBytes(part,bytes[..4]);
using(var client=new HttpClient(new FakeHandler(req=>new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=req,Content=new ByteArrayContent(bytes)})))
 await Installer.Download(client,download,part,progress,CancellationToken.None);
Check(await Installer.Matches(part,download,CancellationToken.None),"200 restarts rather than appends");
File.WriteAllBytes(part,bytes[..4]);
using(var client=new HttpClient(new FakeHandler(req=>new HttpResponseMessage(HttpStatusCode.PartialContent){RequestMessage=req,Content=new ByteArrayContent(bytes)})))
 await Reject(()=>Installer.Download(client,download,part,progress,CancellationToken.None),"bad range");
var local=Path.Combine(folder,"payloads"); Directory.CreateDirectory(local);
File.WriteAllBytes(Path.Combine(local,"model.gguf"),[1,2,3]);
var copied=Path.Combine(folder,"local.part"); File.WriteAllBytes(copied,[1]);
await LocalPayload.Copy(local,payloads[1],copied,progress,CancellationToken.None);
Check(await Installer.Matches(copied,payloads[1],CancellationToken.None),"offline resume");
await Reject(()=>LocalPayload.Copy(local,payloads[1] with{Name="../escape"},copied,progress,CancellationToken.None),"offline unsafe path");
File.WriteAllBytes(Path.Combine(local,"model.gguf"),[1]);
await Reject(()=>LocalPayload.Copy(local,payloads[1],copied,progress,CancellationToken.None),"offline wrong length");
Console.WriteLine($"{checks} installer checks passed; fixtures retained at {folder}");

sealed class FakeHandler(Func<HttpRequestMessage,HttpResponseMessage> respond) : HttpMessageHandler
{
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken cancellationToken)=>Task.FromResult(respond(request));
}
