using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace NpcChat.Desktop;

internal sealed class DiagnosticsWindow : Window
{
    private readonly TextBlock status = new() { TextWrapping = TextWrapping.Wrap, FontSize = 16, Margin = new Thickness(0, 12, 0, 20) };
    private readonly Button retry = new() { Content = "다시 시도", Margin = new Thickness(0, 8, 0, 8) };
    private readonly List<object> events = new();
    private readonly Stopwatch elapsed = Stopwatch.StartNew();
    private readonly bool packaged;
    public string LastCode { get; private set; } = "configuration";
    public static readonly Dictionary<string, string> Messages = new() {
        ["configuration"] = "실행 파일과 설정을 확인하고 있어요.",
        ["ports"] = "다른 서버가 실행 중인지 확인하고 있어요.",
        ["model_check"] = "모델과 그래픽카드를 확인하고 있어요.",
        ["model_loading"] = "모델을 메모리에 올리고 있어요. 처음에는 시간이 걸릴 수 있어요.",
        ["server_loading"] = "대화 서버를 준비하고 있어요.",
        ["chat_loading"] = "채팅 화면을 준비하고 있어요.",
        ["ready"] = "대화할 준비가 됐어요.",
        ["PORT_BUSY"] = "다른 서버가 같은 연결 포트를 사용하고 있어요. 기존 NPC Chat 서버를 정상 종료한 후 다시 시도하세요.",
        ["LOW_VRAM"] = "사용 가능한 GPU 메모리가 부족해요. 게임이나 다른 AI 프로그램을 종료한 후 다시 시도하세요.",
        ["GPU_OR_ENGINE_CHECK_FAILED"] = "그래픽카드 또는 추론 엔진을 확인하지 못했어요. NVIDIA 드라이버와 패키지 파일을 확인하세요. 정확한 원인은 추가 점검이 필요해요.",
        ["MODEL_MISSING"] = "모델 파일을 찾지 못했어요. 모델을 포함한 폴더 전체를 복사했는지 확인하세요.",
        ["ENGINE_MISSING"] = "추론 엔진을 찾지 못했어요. 패키지의 runtime 폴더를 확인하세요.",
        ["ENGINE_INCOMPATIBLE"] = "추론 엔진 버전이 맞지 않아요. 검증된 패키지로 복원하세요.",
        ["PACKAGE_INVALID"] = "패키지 설정 또는 필수 파일이 올바르지 않아요. 폴더 전체가 복사됐는지 확인하세요.",
        ["PYTHON_MISSING"] = "Python 실행 환경이 없어요. 패키지의 runtime 폴더를 확인하세요.",
        ["WEBVIEW_FAILED"] = "채팅 화면을 열지 못했어요. 동봉된 WebView2 파일과 폴더 접근 권한을 확인하세요.",
        ["START_TIMEOUT"] = "준비 시간이 초과됐어요. 다른 작업을 종료한 후 다시 시도하세요. 파일·드라이버 문제일 수도 있어요.",
        ["PROCESS_EXITED"] = "서버 또는 모델이 종료됐어요. 다시 시도해도 같다면 진단 파일을 저장해 주세요.",
        ["ALREADY_STARTING"] = "다른 실행 작업이 진행 중이에요. 해당 작업이 끝난 뒤 다시 시도하세요.",
        ["ACCESS_DENIED"] = "파일 접근 권한이 없어요. 쓰기 가능한 폴더와 보안 프로그램의 차단 여부를 확인하세요.",
        ["START_CANCELLED"] = "시작을 취소했어요.",
        ["START_FAILED"] = "실행하지 못했어요. 원인이 확인되지 않았습니다. 다시 시도해도 같다면 진단 파일을 저장해 주세요."
    };
    public DiagnosticsWindow(App owner, bool isPackaged)
    {
        packaged = isPackaged; Title = "NPC Chat · 실행 상태"; Width = 450; Height = 400;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        var panel = new StackPanel { Margin = new Thickness(24) };
        panel.Children.Add(new TextBlock { Text = "실행 상태와 문제 해결", FontSize = 21, FontWeight = FontWeights.SemiBold });
        panel.Children.Add(status);
        retry.Click += async (_, _) => await owner.Retry(); panel.Children.Add(retry);
        var save = new Button { Content = "진단 파일 저장 (대화 내용 제외)" };
        save.Click += (_, _) => {
            var dialog = new Microsoft.Win32.SaveFileDialog { Filter = "진단 파일 (*.json)|*.json", FileName = "npc-chat-diagnostics.json" };
            if (dialog.ShowDialog(this) == true) {
                try { Save(dialog.FileName); MessageBox.Show(this, "진단 파일을 저장했어요."); }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { MessageBox.Show(this, "파일을 저장하지 못했어요. 다른 폴더를 선택하세요."); }
            }
        };
        panel.Children.Add(save); Content = panel;
        Closing += (_, e) => { if (!owner.Exiting) { e.Cancel = true; Hide(); } };
    }
    public void Update(string code, bool canRetry)
    {
        LastCode = Messages.ContainsKey(code) ? code : "START_FAILED";
        status.Text = Messages[LastCode] + "\n\n상태 코드: " + LastCode;
        retry.IsEnabled = canRetry;
        events.Add(new { elapsedSeconds = Math.Round(elapsed.Elapsed.TotalSeconds, 1), code = LastCode });
        if (events.Count > 64) events.RemoveAt(0);
    }
    public void Save(string path) => File.WriteAllText(path, JsonSerializer.Serialize(new {
        format = 1, appVersion = typeof(App).Assembly.GetName().Version?.ToString(),
        osVersion = Environment.OSVersion.Version.ToString(), is64Bit = Environment.Is64BitProcess,
        packaged, events,
    }, new JsonSerializerOptions { WriteIndented = true }));
}
