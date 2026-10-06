using System.IO.Compression;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using NpcChat.Setup;

if (args.Length == 3 && args[0] == "--hf-probe") {
 using var client = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false });
 var info = new FileInfo(args[2]); long offset = info.Length - 1024 * 1024;
 using var response = await Installer.SendDownload(client, new Uri(args[1]), offset, CancellationToken.None);
 if (response.StatusCode != HttpStatusCode.PartialContent || response.Content.Headers.ContentRange?.From != offset
     || response.Content.Headers.ContentRange?.Length != info.Length) throw new Exception("HF Range response mismatch");
 await using var stream = await response.Content.ReadAsStreamAsync();
 var actual = new byte[1024*1024]; await stream.ReadExactlyAsync(actual);
 if (stream.ReadByte() != -1) throw new Exception("HF range too long");
 await using var model = File.OpenRead(args[2]); model.Position = offset;
 var expected = new byte[actual.Length]; await model.ReadExactlyAsync(expected);
 if (!actual.SequenceEqual(expected)) throw new Exception("HF model bytes mismatch");
 Console.WriteLine(JsonSerializer.Serialize(new {passed=true,bytes=actual.Length,total=info.Length,host=response.RequestMessage?.RequestUri?.Host,range=true}));
 return;
}

var checks = 0;
void Check(bool b, string name) { if (!b) throw new Exception(name); checks++; }
async Task Reject(Func<Task> action, string name) { try { await action(); } catch (Exception e) when (e is IOException or InvalidDataException or InvalidOperationException or OperationCanceledException or HttpRequestException) { checks++; return; } throw new Exception(name); }
string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
var folder = Path.Combine(Path.GetTempPath(), "npc-setup-checks-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(folder);
var fixture = Path.Combine(folder,"fixture"); Directory.CreateDirectory(fixture);
var names = new[] { "NpcChat.Desktop.exe", "desktop-package.json", "app/owned.py", "runtime/python/python.exe", "runtime/llama/llama-server.exe", "runtime/webview2/msedgewebview2.exe", "models/model.gguf" };
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
Check(!Directory.EnumerateFiles(Path.Combine(root,"cache")).Any(),"successful install removes payload cache");
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
Check(!Directory.EnumerateDirectories(Path.Combine(canceledRoot,"staging")).Any(),"canceled attempt removes its staging");
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
// Failure boundaries beyond the original happy path and resume checks.
await Reject(()=>Task.FromResult(Installer.ReadRelease(JsonSerializer.Serialize(release with{Payloads=[null!,payloads[1]]}))),"null payload rejected");
var preCanceled=Path.Combine(folder,"pre-canceled");
await Reject(()=>Installer.Install(release,preCanceled,acquire,progress,new CancellationToken(true)),"pre-canceled install");
Check(!Directory.Exists(preCanceled),"pre-canceled install writes nothing");
var sizeRoot=Path.Combine(folder,"size");Directory.CreateDirectory(Path.Combine(sizeRoot,"cache"));
var emptyRequirement=Installer.RequiredSpace(release,sizeRoot);
File.WriteAllBytes(Path.Combine(sizeRoot,"cache",payloads[1].Sha256+".part"),[1,2,3]);
Check(Installer.RequiredSpace(release,sizeRoot)==emptyRequirement-3,"space estimate credits cached bytes");
var locked=Path.Combine(folder,"locked"); Directory.CreateDirectory(locked);
using(var guard=new FileStream(Path.Combine(locked,"install.lock"),FileMode.Create,FileAccess.ReadWrite,FileShare.None))
 await Reject(()=>Installer.Install(release,locked,acquire,progress,CancellationToken.None),"concurrent installer rejected");
Check(!File.Exists(Path.Combine(locked,"current.json")),"concurrent attempt stays inactive");
// Fail after extraction: clean only this attempt, retain payloads and unrelated old staging.
var late=Path.Combine(folder,"late-cancel");Directory.CreateDirectory(Path.Combine(late,"staging","old-attempt"));
File.WriteAllText(Path.Combine(late,"staging","old-attempt","keep"),"keep");
using(var cancel=new CancellationTokenSource()) {
 var cancelProgress=new InlineProgress(p=>{if(p.Stage=="모델 설치 중")cancel.Cancel();});
 await Reject(()=>Installer.Install(release,late,acquire,cancelProgress,cancel.Token),"cancel after extraction");
}
Check(!File.Exists(Path.Combine(late,"current.json")),"late cancellation stays inactive");
Check(Directory.GetDirectories(Path.Combine(late,"staging")).Length==1,"only own staging removed");
Check(File.ReadAllText(Path.Combine(late,"staging","old-attempt","keep"))=="keep","old staging preserved");
Check(Directory.GetFiles(Path.Combine(late,"cache")).Length==2,"cancel keeps resumable cache");
await Installer.Install(release,late,(_,_,_,_)=>throw new Exception("valid cache downloaded again"),progress,CancellationToken.None);
Check(!Directory.EnumerateFiles(Path.Combine(late,"cache")).Any(),"retry clears successful cache");
async Task BadArchive(string label, Action<ZipArchive> write, long bound=100000) {
 var badZip=Path.Combine(folder,label+".zip");
 using(var archive=ZipFile.Open(badZip,ZipArchiveMode.Create))write(archive);
 var content=File.ReadAllBytes(badZip);
 var r=release with{ExpandedBytes=bound,Payloads=[new Payload("app.zip",content.Length,Hash(content)),payloads[1]]};
 var dest=Path.Combine(folder,label);
 await Reject(()=>Installer.Install(r,dest,(p,d,_,_)=>File.WriteAllBytesAsync(d,p.Name=="app.zip"?content:new byte[]{1,2,3}),progress,CancellationToken.None),label);
 Check(!File.Exists(Path.Combine(dest,"current.json")),label+" stays inactive");
 Check(!Directory.EnumerateDirectories(Path.Combine(dest,"staging")).Any(),label+" staging removed");
}
void Entry(ZipArchive zip,string name,string content) { using var writer=new StreamWriter(zip.CreateEntry(name).Open());writer.Write(content); }
await BadArchive("case-duplicate",z=>{Entry(z,"a.txt","one");Entry(z,"A.txt","two");});
await BadArchive("model-in-app",z=>Entry(z,"models/model.gguf","bad"));
await BadArchive("expanded-bound",z=>Entry(z,"large.txt",new string('x',200)),100);
await BadArchive("unix-symlink",z=>{var entry=z.CreateEntry("linked");entry.ExternalAttributes=unchecked((int)0xA1FF0000);});
await BadArchive("missing-manifest",z=>Entry(z,"test.txt","missing"));
File.WriteAllBytes(part,new byte[bytes.Length]);
using(var client=new HttpClient(new FakeHandler(req=>{
 Check(req.Headers.Range==null,"corrupt full cache restarts");
 return new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=req,Content=new ByteArrayContent(bytes)};
}))) await Installer.Download(client,download,part,progress,CancellationToken.None);
Check(await Installer.Matches(part,download,CancellationToken.None),"corrupt cache recovered");
File.Delete(part);
using(var client=new HttpClient(new FakeHandler(req=>new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=req,Content=new ByteArrayContent(bytes[..3])})))
 await Reject(()=>Installer.Download(client,download,part,progress,CancellationToken.None),"short response");
using(var client=new HttpClient(new FakeHandler(req=>new HttpResponseMessage(HttpStatusCode.Found){RequestMessage=req,Content=new ByteArrayContent([])})))
 await Reject(()=>Installer.Download(client,download,part,progress,CancellationToken.None),"redirect blocked");
using(var client=new HttpClient(new FakeHandler(req=>new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=new HttpRequestMessage(HttpMethod.Get,"http://example.invalid/model"),Content=new ByteArrayContent(bytes)})))
 await Reject(()=>Installer.Download(client,download,part,progress,CancellationToken.None),"HTTPS downgrade rejected");
if(OperatingSystem.IsWindows()) {
 var linkPath=Path.Combine(folder,"NPC Chat.lnk");
 SetupShortcut.Create(installed,linkPath);
 var linkBytes=File.ReadAllBytes(linkPath);
 Check(linkBytes.Length>0,"real shortcut created in test directory");
 SetupShortcut.Create(installed,linkPath);
 Check(File.ReadAllBytes(linkPath).SequenceEqual(linkBytes),"matching shortcut preserved");
 await Reject(()=>{SetupShortcut.Create(Path.Combine(folder,"unrelated"),linkPath);return Task.CompletedTask;},"unrelated shortcut rejected");
 Check(File.ReadAllBytes(linkPath).SequenceEqual(linkBytes),"unrelated shortcut unchanged");
}
var protectedData = Path.Combine(folder,"user-data");
var sourceFolder = Path.Combine(folder,"source");
var freshRoot = Path.Combine(folder,"새 설치 위치");
Check(SetupOptions.ValidateRoot(freshRoot,release,sourceFolder,protectedData)==freshRoot,"custom install location");
Check(!Directory.Exists(freshRoot),"path validation is read only");
Check(SetupOptions.ValidateRoot(canceledRoot,release,sourceFolder,protectedData)==canceledRoot,"same release path accepted");
foreach(var bad in new[]{"relative","",Path.GetPathRoot(folder)!,protectedData,Path.Combine(protectedData,"child"),folder,sourceFolder,Path.Combine(sourceFolder,"child")})
 await Reject(()=>Task.FromResult(SetupOptions.ValidateRoot(bad,release,sourceFolder,protectedData)),"reject unsafe install location "+bad);
var occupied = Path.Combine(folder,"occupied"); Directory.CreateDirectory(occupied); File.WriteAllText(Path.Combine(occupied,"personal.txt"),"keep");
await Reject(()=>Task.FromResult(SetupOptions.ValidateRoot(occupied,release,sourceFolder,protectedData)),"unrelated directory rejected");
Check(File.ReadAllText(Path.Combine(occupied,"personal.txt"))=="keep","personal file preserved");
await Reject(()=>Task.FromResult(SetupOptions.ValidateRoot(canceledRoot,release with{Id="new-version"},sourceFolder,protectedData)),"existing version rejected before install");
Check(!SetupOptions.CanDownload(release),"unconfigured online disabled");
Check(SetupOptions.CanDownload(release with{Payloads=release.Payloads.Select(p=>p with{Url="https://example.invalid/"+p.Name}).ToArray()}),"configured online enabled");
Check(!SetupOptions.HasLocal(release,sourceFolder),"missing payload disabled");
Directory.CreateDirectory(sourceFolder); File.Copy(zip,Path.Combine(sourceFolder,"app.zip")); File.WriteAllBytes(Path.Combine(sourceFolder,"model.gguf"),[1,2,3]);
Check(SetupOptions.HasLocal(release,sourceFolder),"complete offline source enabled");
File.WriteAllBytes(Path.Combine(sourceFolder,"model.gguf"),[1]);
Check(!SetupOptions.HasLocal(release,sourceFolder),"incomplete offline source disabled");
var hfPayload=download with{Url="https://huggingface.co/owner/repo/resolve/commit/model.gguf"};
File.WriteAllBytes(part,bytes[..3]);
int hfCalls=0;
using(var client=new HttpClient(new FakeHandler(req=>{
 Check(req.Headers.Range?.Ranges.Single().From==3,"HF preserves resume offset");
 if(hfCalls++==0) { var redirect=new HttpResponseMessage(HttpStatusCode.Found){RequestMessage=req}; redirect.Headers.Location=new Uri("https://us.aws.cdn.hf.co/file?signed=temporary"); return redirect; }
 var result=new HttpResponseMessage(HttpStatusCode.PartialContent){RequestMessage=req,Content=new ByteArrayContent(bytes[3..])};
 result.Content.Headers.ContentRange=new ContentRangeHeaderValue(3,bytes.Length-1,bytes.Length);return result;
}))) await Installer.Download(client,hfPayload,part,progress,CancellationToken.None);
Check(await Installer.Matches(part,hfPayload,CancellationToken.None),"HF redirected bytes verified");
foreach(var target in new[]{"http://us.aws.cdn.hf.co/file","https://us.aws.cdn.hf.co.evil.test/file","https://evil.test/file","https://user:secret@us.aws.cdn.hf.co/file","https://us.aws.cdn.hf.co:8443/file"}) {
 using var client=new HttpClient(new FakeHandler(req=>{var result=new HttpResponseMessage(HttpStatusCode.Found){RequestMessage=req};result.Headers.Location=new Uri(target);return result;}));
 await Reject(()=>Installer.SendDownload(client,new Uri(hfPayload.Url!),0,CancellationToken.None),"unsafe HF redirect "+target);
}
using(var client=new HttpClient(new FakeHandler(req=>{var result=new HttpResponseMessage(HttpStatusCode.Found){RequestMessage=req};result.Headers.Location=new Uri("https://huggingface.co/loop");return result;})))
 await Reject(()=>Installer.SendDownload(client,new Uri(hfPayload.Url!),0,CancellationToken.None),"HF redirect loop bounded");
File.WriteAllBytes(part,bytes[..3]);
using(var client=new HttpClient(new FakeHandler(req=>new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=req,Content=new StringContent("<html>confirmation or quota</html>",Encoding.UTF8,"text/html")})))
 await Reject(()=>Installer.Download(client,download,part,progress,CancellationToken.None),"HTML download page rejected");
Check(File.ReadAllBytes(part).SequenceEqual(bytes[..3]),"HTML response preserves resumable cache");
if (OperatingSystem.IsWindows()) {
 var fakeSetup = Path.Combine(folder,"setup-fixture.exe"); File.WriteAllText(fakeSetup,"owned uninstaller fixture");
 var registryBase = @"Software\NpcChat\SetupTests\" + Guid.NewGuid().ToString("N");
 foreach (var keepData in new[]{true,false}) foreach(var keepModel in new[]{true,false}) {
  var caseRoot=Path.Combine(folder,$"remove-{keepData}-{keepModel}");
  var scopeRoot=Path.Combine(folder,$"scope-{keepData}-{keepModel}");
  var scope=new WindowsScope(Path.Combine(scopeRoot,"Programs"),Path.Combine(scopeRoot,"Desktop"),Path.Combine(scopeRoot,"UserData"),registryBase);
  Directory.CreateDirectory(scope.Desktop); Directory.CreateDirectory(Path.Combine(scope.Data,"browser"));
  File.WriteAllText(Path.Combine(scope.Data,"browser","identity"),"preserve session");
  File.WriteAllText(Path.Combine(scope.Data,"chat.db"),"preserve conversations");
  var result=await Installer.Install(release,caseRoot,acquire,progress,CancellationToken.None);
  var bytecode=Path.Combine(result,"app","__pycache__","owned.cpython-312.pyc");
  Directory.CreateDirectory(Path.GetDirectoryName(bytecode)!); File.WriteAllText(bytecode,"generated cache");
  WindowsInstall.Register(caseRoot,release,fakeSetup,true,scope);
  SetupShortcut.Create(result,Path.Combine(scope.Desktop,"NPC Chat.lnk"));
  if(!keepData && !keepModel) { File.Delete(Path.Combine(scope.Desktop,"NPC Chat.lnk")); SetupShortcut.Create(Path.Combine(scopeRoot,"other-app"),Path.Combine(scope.Desktop,"NPC Chat.lnk")); }
  using(var key=Microsoft.Win32.Registry.CurrentUser.OpenSubKey(registryBase+"\\"+WindowsInstall.Identity(caseRoot))) {
   Check(key?.GetValue("DisplayName") as string == "NPC Chat","installed apps display name");
   Check((key?.GetValue("UninstallString") as string)?.Contains("--uninstall") == true,"uninstall command registered");
  }
  Check(File.Exists(Path.Combine(WindowsInstall.MenuFolder(caseRoot,scope),"NPC Chat.lnk")),"start menu created");
  if(keepData && keepModel) {
   var statePath=Path.Combine(caseRoot,WindowsInstall.StateName);
   var savedState=File.ReadAllText(statePath);
   var parsedState=JsonSerializer.Deserialize<InstallOwnership>(savedState)!;
   File.WriteAllText(statePath,JsonSerializer.Serialize(parsedState with{Root=folder}));
   await Reject(()=>Task.Run(()=> {if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,true,true,scope);}),"tampered root rejected");
   File.WriteAllText(statePath,savedState);
   await Reject(()=>Task.Run(()=> {if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,false,true,scope with{Data=caseRoot});}),"data/install overlap rejected");
   var outside=Path.Combine(scopeRoot,"outside"); Directory.CreateDirectory(outside); File.WriteAllText(Path.Combine(outside,"keep.txt"),"external");
   var junction=Path.Combine(caseRoot,"external-link");
   var junctionStart=new System.Diagnostics.ProcessStartInfo("powershell.exe"){UseShellExecute=false,CreateNoWindow=true};
   junctionStart.ArgumentList.Add("-NoProfile"); junctionStart.ArgumentList.Add("-Command");
   junctionStart.ArgumentList.Add("$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path '"+junction.Replace("'","''")+"' -Target '"+outside.Replace("'","''")+"' | Out-Null");
   using(var maker=System.Diagnostics.Process.Start(junctionStart)!) {maker.WaitForExit();Check(maker.ExitCode==0,"junction fixture created");}
   await Reject(()=>Task.Run(()=> {if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,true,true,scope);}),"junction rejected before deletion");
   Check(File.ReadAllText(Path.Combine(outside,"keep.txt"))=="external","junction target preserved");
   Directory.Delete(junction,false);
   var mutexKey=Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(scope.Data).ToUpperInvariant())));
   using(var appMutex=new Mutex(false,"Local\\NpcChatDesktop-"+mutexKey))
    await Reject(()=>Task.Run(()=> {if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,true,true,scope);}),"live app mutex blocks removal");
   // A locked app file and tampered ownership/manifest must reject before data loss.
   using(var held=new FileStream(Path.Combine(result,"NpcChat.Desktop.exe"),FileMode.Open,FileAccess.Read,FileShare.Read))
    await Reject(()=>Task.Run(()=> { if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,true,true,scope); }),"running file blocks removal");
   Check(File.Exists(Path.Combine(result,"runtime/python/python.exe")),"locked file preserves installation");
   File.AppendAllText(Path.Combine(result,"package-manifest.json")," ");
   await Reject(()=>Task.Run(()=> { if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,true,true,scope); }),"tampered manifest blocks removal");
   File.WriteAllText(Path.Combine(result,"package-manifest.json"),manifest);
   File.WriteAllText(Path.Combine(caseRoot,"user-notes.txt"),"not ours");
   Directory.CreateDirectory(Path.Combine(caseRoot,"user-empty-folder"));
  }
  await Task.Run(()=> { if(OperatingSystem.IsWindows()) WindowsInstall.Remove(caseRoot,release,keepData,keepModel,scope); });
  Check(!File.Exists(Path.Combine(result,"NpcChat.Desktop.exe")),"owned app removed");
  Check(!File.Exists(bytecode),"owned source bytecode removed");
  Check(Directory.Exists(scope.Data)==keepData,"data preservation choice");
  Check(File.Exists(WindowsInstall.RetainedModel(caseRoot,release))==keepModel,"model preservation choice");
  if(keepModel) Check(File.ReadAllBytes(WindowsInstall.RetainedModel(caseRoot,release)).SequenceEqual(new byte[]{1,2,3}),"retained model bytes unchanged");
  Check(File.Exists(Path.Combine(scope.Desktop,"NPC Chat.lnk"))==(!keepData && !keepModel),"owned desktop removed / foreign desktop preserved");
  Check(!Directory.Exists(WindowsInstall.MenuFolder(caseRoot,scope)),"owned start menu removed");
  using(var key=Microsoft.Win32.Registry.CurrentUser.OpenSubKey(registryBase+"\\"+WindowsInstall.Identity(caseRoot))) Check(key==null,"installed apps entry removed");
  if(keepData && keepModel) {Check(File.ReadAllText(Path.Combine(caseRoot,"user-notes.txt"))=="not ours","unknown file preserved");Check(Directory.Exists(Path.Combine(caseRoot,"user-empty-folder")),"unknown empty directory preserved");}
 }
 Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(registryBase,false);
}
Console.WriteLine($"{checks} installer checks passed; fixtures retained at {folder}");

sealed class FakeHandler(Func<HttpRequestMessage,HttpResponseMessage> respond) : HttpMessageHandler
{
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken cancellationToken)=>Task.FromResult(respond(request));
}

sealed class InlineProgress(Action<InstallProgress> action) : IProgress<InstallProgress>
{
 public void Report(InstallProgress value)=>action(value);
}
