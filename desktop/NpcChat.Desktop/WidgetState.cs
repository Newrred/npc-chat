using System;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace NpcChat.Desktop;

public record WorkArea(string Id, int X, int Y, int Width, int Height);
public record WidgetState(int Version = 1, double Scale = 1, bool Compact = false, bool Topmost = true,
                          string Monitor = "", double X = 1, double Y = 1,
                          double? LegacyLeft = null, double? LegacyTop = null)
{
    public WidgetState Validated() => this with {
        Version = 1, Scale = double.IsFinite(Scale) ? Math.Clamp(Scale, .75, 1.6) : 1,
        X = double.IsFinite(X) ? Math.Clamp(X, 0, 1) : 1,
        Y = double.IsFinite(Y) ? Math.Clamp(Y, 0, 1) : 1,
        Monitor = Monitor ?? ""
    };
    public static WidgetState Load(string path)
    {
        try {
            var text = File.ReadAllText(path);
            using var doc = JsonDocument.Parse(text);
            if (doc.RootElement.ValueKind == JsonValueKind.Array) {
                var old = JsonSerializer.Deserialize<double[]>(text);
                return old?.Length == 2 && double.IsFinite(old[0]) && double.IsFinite(old[1])
                    ? new(LegacyLeft: old[0], LegacyTop: old[1]) : new();
            }
            var state = JsonSerializer.Deserialize<WidgetState>(text);
            return state?.Version == 1 ? state.Validated() : new();
        } catch (Exception ex) when (ex is IOException or JsonException or UnauthorizedAccessException) { return new(); }
    }
    public void Save(string path)
    {
        var temporary = path + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(Validated()));
        File.Move(temporary, path, true);
    }
    public (int X, int Y) Position(WorkArea area, int width, int height)
    {
        var state = Validated();
        return (area.X + (int)Math.Round(Math.Max(0, area.Width - width) * state.X),
                area.Y + (int)Math.Round(Math.Max(0, area.Height - height) * state.Y));
    }
    public static WorkArea Select(string id, WorkArea[] areas) =>
        areas.FirstOrDefault(a => a.Id == id) ?? areas[0];
}
