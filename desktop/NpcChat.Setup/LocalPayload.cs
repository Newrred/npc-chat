using System.IO;

namespace NpcChat.Setup;

public static class LocalPayload
{
    public static async Task Copy(string root, Payload payload, string dest, IProgress<InstallProgress> progress, CancellationToken ct)
    {
        var inputPath = Installer.SafePath(root, payload.Name);
        if (new FileInfo(inputPath).Length != payload.Bytes) throw new InvalidDataException("동봉 파일 크기가 다릅니다.");
        long offset = File.Exists(dest) ? new FileInfo(dest).Length : 0;
        if (offset == payload.Bytes && await Installer.Matches(dest, payload, ct)) return;
        if (offset >= payload.Bytes) offset = 0;
        await using var input = File.OpenRead(inputPath); input.Position = offset;
        await using var output = new FileStream(dest, offset == 0 ? FileMode.Create : FileMode.Append, FileAccess.Write, FileShare.None);
        var buffer = new byte[1024 * 1024]; long done = offset;
        while (done < payload.Bytes) {
            var n = await input.ReadAsync(buffer.AsMemory(0, (int)Math.Min(buffer.Length, payload.Bytes - done)), ct);
            if (n == 0) throw new IOException("동봉 파일을 끝까지 읽지 못했습니다.");
            await output.WriteAsync(buffer.AsMemory(0,n), ct); done += n;
            progress.Report(new("동봉 파일 준비 · " + payload.Name, done, payload.Bytes));
        }
    }
}
