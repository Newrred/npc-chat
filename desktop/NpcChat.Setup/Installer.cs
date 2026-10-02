using System.IO.Compression;
using System.IO;
using System.Net.Http;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace NpcChat.Setup;

public record Payload(string Name, long Bytes, string Sha256, string? Url = null);
public record Release(int Format, string Id, long ExpandedBytes, string Distribution, string ManifestSha256, Payload[] Payloads);
public record InstallProgress(string Stage, long Done = 0, long Total = 0);
public delegate Task Acquire(Payload payload, string destination, IProgress<InstallProgress> progress, CancellationToken cancel);

public static class Installer
{
    public static readonly JsonSerializerOptions Json = new() { PropertyNameCaseInsensitive = true, UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow };
    public static Release ReadRelease(string text)
    {
        var r = JsonSerializer.Deserialize<Release>(text, Json) ?? throw new InvalidDataException("설치 정보가 없습니다.");
        if (r.Format != 1 || r.Distribution != "internal-test-only" || r.Id == null || !Regex.IsMatch(r.Id, "^[a-zA-Z0-9][a-zA-Z0-9.-]{0,63}$") || r.Id.Contains("..") || r.ExpandedBytes <= 0 || r.Payloads?.Length != 2)
            throw new InvalidDataException("지원하지 않는 설치 정보입니다.");
        if (!r.Payloads.Select(p => p.Name).Order().SequenceEqual(new[] { "app.zip", "model.gguf" })) throw new InvalidDataException("설치 파일 구성이 잘못되었습니다.");
        if (r.ManifestSha256 == null || !Regex.IsMatch(r.ManifestSha256, "^[a-f0-9]{64}$")) throw new InvalidDataException("패키지 검증 정보 누락");
        foreach (var p in r.Payloads) {
            if (p.Bytes <= 0 || p.Sha256 == null || !Regex.IsMatch(p.Sha256, "^[a-f0-9]{64}$")) throw new InvalidDataException("파일 검증 정보가 잘못되었습니다.");
            if (p.Url != null && (!Uri.TryCreate(p.Url, UriKind.Absolute, out var u) || u.Scheme != "https" || !string.IsNullOrEmpty(u.UserInfo) || !string.IsNullOrEmpty(u.Fragment))) throw new InvalidDataException("HTTPS 배포 주소가 필요합니다.");
        }
        return r;
    }
    public static string SafePath(string root, string relative)
    {
        if (string.IsNullOrWhiteSpace(relative) || relative.Contains('\\') || relative.Contains(':') || relative.StartsWith('/') || relative.Contains('\0')) throw new InvalidDataException("안전하지 않은 파일 경로입니다.");
        foreach (var part in relative.Split('/')) {
            if (part is "" or "." or ".." || part.EndsWith(' ') || part.EndsWith('.') || part.IndexOfAny(['<','>','"','|','?','*']) >= 0 || part.Any(char.IsControl)
                || Regex.IsMatch(part.Split('.')[0], "^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])$", RegexOptions.IgnoreCase)) throw new InvalidDataException("안전하지 않은 파일 이름입니다.");
        }
        var result = Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)));
        if (!result.StartsWith(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("설치 경로를 벗어났습니다.");
        RejectLinks(result);
        return result;
    }
    public static void RejectLinks(string path)
    {
        for (var p = Path.GetFullPath(path); p != null; p = Path.GetDirectoryName(p)) {
            if ((File.Exists(p) || Directory.Exists(p)) && (File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("연결된 폴더에는 설치할 수 없습니다.");
        }
    }
    public static async Task<bool> Matches(string path, Payload p, CancellationToken ct)
    {
        if (!File.Exists(path) || new FileInfo(path).Length != p.Bytes) return false;
        await using var s = File.OpenRead(path);
        return Convert.ToHexString(await SHA256.HashDataAsync(s, ct)).Equals(p.Sha256, StringComparison.OrdinalIgnoreCase);
    }
    public static async Task Download(HttpClient http, Payload p, string destination, IProgress<InstallProgress> progress, CancellationToken ct)
    {
        if (p.Url == null) throw new InvalidDataException("다운로드 주소가 아직 설정되지 않았습니다.");
        long offset = File.Exists(destination) ? new FileInfo(destination).Length : 0;
        if (offset == p.Bytes && await Matches(destination, p, ct)) return;
        if (offset >= p.Bytes) offset = 0;
        using var req = new HttpRequestMessage(HttpMethod.Get, p.Url);
        if (offset > 0) req.Headers.Range = new RangeHeaderValue(offset, null);
        using var response = await http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();
        if (response.RequestMessage?.RequestUri?.Scheme != "https") throw new InvalidDataException("HTTPS 연결만 허용합니다.");
        if (response.StatusCode == HttpStatusCode.PartialContent) {
            var range = response.Content.Headers.ContentRange;
            if (range?.Unit != "bytes" || range.From != offset || range.To != p.Bytes - 1 || range.Length != p.Bytes) throw new InvalidDataException("이어받기 범위가 잘못되었습니다.");
        } else if (response.StatusCode == HttpStatusCode.OK) offset = 0;
        else throw new InvalidDataException("다운로드 응답을 확인할 수 없습니다.");
        if (response.Content.Headers.ContentLength is long size && size != p.Bytes - offset) throw new InvalidDataException("다운로드 크기가 일치하지 않습니다.");
        await using var input = await response.Content.ReadAsStreamAsync(ct);
        await using (var output = new FileStream(destination, offset > 0 ? FileMode.Append : FileMode.Create, FileAccess.Write, FileShare.None)) {
            var buffer = new byte[1024 * 1024]; long received = offset;
            while (true) {
                var n = await input.ReadAsync(buffer, ct); if (n == 0) break;
                if (received + n > p.Bytes) throw new InvalidDataException("다운로드가 지정 크기를 초과했습니다.");
                await output.WriteAsync(buffer.AsMemory(0, n), ct); received += n;
                progress.Report(new("파일 받는 중 · " + p.Name, received, p.Bytes));
            }
            await output.FlushAsync(ct);
            if (received != p.Bytes) throw new IOException("다운로드가 중단됐습니다. 다시 시도하면 이어받습니다.");
        }
        if (!await Matches(destination, p, ct)) throw new InvalidDataException("다운로드 검증 실패. 다시 시도하면 새로 받습니다.");
    }
    public static async Task<string> Install(Release r, string root, Acquire acquire, IProgress<InstallProgress> progress, CancellationToken ct)
    {
        ReadRelease(JsonSerializer.Serialize(r)); // Same validation for API/test callers.
        root = Path.GetFullPath(root); RejectLinks(root); Directory.CreateDirectory(root);
        await using var guard = new FileStream(SafePath(root, "install.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        var current = SafePath(root, "current.json");
        if (File.Exists(current)) {
            var active = JsonSerializer.Deserialize<string>(await File.ReadAllTextAsync(current, ct));
            if (active != r.Id) throw new InvalidOperationException("다른 버전이 설치되어 있습니다. 이 내부 시험 설치기는 버전 업데이트를 아직 지원하지 않습니다.");
            var installed = SafePath(root, "releases/" + r.Id);
            await VerifyInstalled(installed, ct, r.ManifestSha256); return installed;
        }
        var final = SafePath(root, "releases/" + r.Id);
        if (Directory.Exists(final)) {
            await VerifyInstalled(final, ct, r.ManifestSha256); Activate(root, r.Id); return final;
        }
        var cache = SafePath(root, "cache"); Directory.CreateDirectory(cache);
        // Keep complete old data untouched; interrupted attempts use fresh staging directories.
        var stage = SafePath(root, "staging/" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(stage);
        var needed = checked(r.Payloads.Sum(p => p.Bytes) + r.ExpandedBytes + r.Payloads.Single(p => p.Name == "model.gguf").Bytes + 512L * 1024 * 1024);
        if (new DriveInfo(Path.GetPathRoot(root)!).AvailableFreeSpace < needed) throw new IOException("설치 및 임시 파일을 위한 저장 공간이 부족합니다.");
        var paths = new Dictionary<string,string>();
        foreach (var p in r.Payloads) {
            var path = SafePath(cache, p.Sha256 + ".part"); paths[p.Name] = path;
            if (!await Matches(path, p, ct)) await acquire(p, path, progress, ct);
            progress.Report(new("파일 검증 · " + p.Name));
            if (!await Matches(path, p, ct)) throw new InvalidDataException("파일이 손상되었습니다: " + p.Name);
        }
        progress.Report(new("앱 파일 설치 중"));
        using (var archive = ZipFile.OpenRead(paths["app.zip"])) {
            var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase); long expanded = 0;
            foreach (var entry in archive.Entries) {
                ct.ThrowIfCancellationRequested();
                var name = entry.FullName;
                if (name.EndsWith('/')) { SafePath(stage, name.TrimEnd('/')); continue; }
                var path = SafePath(stage, name);
                if (!names.Add(name) || name.Equals("models/model.gguf", StringComparison.OrdinalIgnoreCase) || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000)
                    throw new InvalidDataException("중복되거나 허용되지 않는 압축 항목입니다.");
                expanded = checked(expanded + entry.Length);
                if (expanded > r.ExpandedBytes) throw new InvalidDataException("압축 해제 크기를 초과했습니다.");
                Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                await using var source = entry.Open(); await using var target = new FileStream(path, FileMode.CreateNew);
                await source.CopyToAsync(target, ct);
                if (target.Length != entry.Length) throw new InvalidDataException("압축 파일 길이가 일치하지 않습니다.");
            }
        }
        progress.Report(new("모델 설치 중"));
        var model = SafePath(stage, "models/model.gguf"); Directory.CreateDirectory(Path.GetDirectoryName(model)!);
        await using (var input = File.OpenRead(paths["model.gguf"]))
        await using (var output = new FileStream(model, FileMode.CreateNew)) await input.CopyToAsync(output, ct);
        progress.Report(new("설치 결과 확인 중")); await VerifyInstalled(stage, ct, r.ManifestSha256); ct.ThrowIfCancellationRequested();
        Directory.CreateDirectory(Path.GetDirectoryName(final)!);
        Directory.Move(stage, final); Activate(root, r.Id);
        progress.Report(new("설치 완료")); return final;
    }
    static void Activate(string root, string id)
    {
        var temp = SafePath(root, "current.json.tmp"); File.WriteAllText(temp, JsonSerializer.Serialize(id));
        File.Move(temp, SafePath(root, "current.json"), true);
    }
    public static async Task VerifyInstalled(string root, CancellationToken ct, string expectedManifest)
    {
        var manifestPath = SafePath(root, "package-manifest.json");
        if (!File.Exists(manifestPath) || !await Matches(manifestPath, new Payload("manifest", new FileInfo(manifestPath).Length, expectedManifest), ct)) throw new InvalidDataException("패키지 목록이 변경됐습니다.");
        using var manifest = JsonDocument.Parse(await File.ReadAllTextAsync(manifestPath, ct));
        if (manifest.RootElement.GetProperty("format").GetInt32() != 1) throw new InvalidDataException("패키지 형식 오류");
        var files = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var f in manifest.RootElement.GetProperty("files").EnumerateArray()) {
            var name = f.GetProperty("path").GetString()!;
            if (!files.Add(name)) throw new InvalidDataException("중복 파일 목록");
            var p = new Payload(name, f.GetProperty("bytes").GetInt64(), f.GetProperty("sha256").GetString()!);
            if (!await Matches(SafePath(root, name), p, ct)) throw new InvalidDataException("설치 파일 검증 실패: " + name);
        }
        foreach (var required in new[] { "NpcChat.Desktop.exe", "desktop-package.json", "models/model.gguf", "runtime/python/python.exe", "runtime/llama/llama-server.exe", "runtime/webview2/msedgewebview2.exe" })
            if (!files.Contains(required)) throw new InvalidDataException("필수 파일 누락: " + required);
    }
}
