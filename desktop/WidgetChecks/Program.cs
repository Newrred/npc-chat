using NpcChat.Desktop;

var count = 0;
void Check(bool condition, string name) { if (!condition) throw new Exception(name); count++; }
var area = new WorkArea("left", -1920, -200, 1920, 1080);
var state = new WidgetState(Scale: 4, X: -2, Y: 7).Validated();
Check(state.Scale == 1.6 && state.X == 0 && state.Y == 1, "clamp invalid bounds");
Check(new WidgetState(Scale: double.NaN, X: double.NaN).Validated().Scale == 1, "nonfinite fallback");
Check(state.Position(area, 200, 300) == (-1920, 580), "negative monitor coordinates");
Check(new WidgetState(X: 1, Y: 1).Position(area, 9000, 9000) == (-1920, -200), "oversized keeps header visible");
var primary = new WorkArea("primary", 0, 0, 2560, 1400);
Check(WidgetState.Select("unplugged", new[] { primary, area }) == primary, "removed monitor falls back");
Check(WidgetState.Select("left", new[] { primary, area }) == area, "secondary is preserved");
var folder = Path.Combine(Path.GetTempPath(), "npc-widget-check-" + Guid.NewGuid());
Directory.CreateDirectory(folder);
var path = Path.Combine(folder, "widget.json");
try {
    var expected = new WidgetState(Scale: 1.3, Compact: true, Topmost: false, Monitor: "left", X: .3, Y: .6);
    expected.Save(path);
    Check(WidgetState.Load(path) == expected, "settings roundtrip");
    var textMode = expected with { Compact = false, TextOnly = true, PreviewReplies = false };
    textMode.Save(path);
    Check(WidgetState.Load(path) == textMode, "text mode and privacy preference roundtrip");
    File.WriteAllText(path, "{\"Version\":1,\"Compact\":true}");
    Check(WidgetState.Load(path).Compact && !WidgetState.Load(path).TextOnly, "old compact preference preserved");
    expected.Save(path);
    Check(!File.Exists(path + ".tmp"), "atomic replace leaves no temp");
    File.WriteAllText(path, "[200, 400]");
    Check(WidgetState.Load(path).LegacyLeft == 200 && WidgetState.Load(path).LegacyTop == 400, "legacy coordinates retained for migration");
    File.WriteAllText(path, "bad json");
    Check(WidgetState.Load(path) == new WidgetState(), "corrupt settings fallback");
    Check(WidgetState.Load(path + "-missing") == new WidgetState(), "missing settings fallback");
} finally { File.Delete(path); Directory.Delete(folder); }
Console.WriteLine($"{count} widget checks passed");
