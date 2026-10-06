using System.ComponentModel;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace NpcChat.Setup;

public partial class UninstallWindow : Window
{
    readonly string root;
    readonly Release release;
    readonly WindowsScope scope;
    readonly Func<bool> confirmDataDeletion;
    bool running, completed;
    public UninstallWindow(string root, Release release, WindowsScope? scope = null, Func<bool>? testConfirmation = null)
    {
        InitializeComponent(); this.root = root; this.release = release; this.scope = scope ?? WindowsScope.Current;
        confirmDataDeletion = testConfirmation ?? (() => MessageBox.Show(this,
            "이 PC의 NPC Chat 대화·기억·관계·브라우저 식별 정보·설정·백업을 모두 삭제합니다. 다른 설치에서도 이 데이터를 사용하며 되돌릴 수 없습니다. 삭제할까요?",
            "대화 기록과 설정 삭제 확인", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) == MessageBoxResult.Yes);
        WindowsInstall.Read(root, release);
        Location.Text = "제거할 앱 위치\n" + root;
        Height = Math.Min(Height, SystemParameters.WorkArea.Height);
        Width = Math.Min(Width, SystemParameters.WorkArea.Width);
        Closing += (_, e) => { if (running) e.Cancel = true; };
    }
    void CloseWindow(object sender, RoutedEventArgs e) => Close();
    async void RemoveClick(object sender, RoutedEventArgs e) => await RemoveAsync();
    internal async Task RemoveAsync()
    {
        if (running || completed) return;
        if (KeepData.IsChecked != true && !confirmDataDeletion()) return;
        running = true; RemoveButton.IsEnabled = false; CloseButton.IsEnabled = false;
        KeepData.IsEnabled = false; KeepModel.IsEnabled = false;
        Status.Text = "앱이 종료됐는지 확인하고 선택한 항목을 제거하고 있어요…";
        var data = KeepData.IsChecked == true; var model = KeepModel.IsChecked == true;
        try {
            await Task.Run(() => WindowsInstall.Remove(root, release, data, model, scope));
            completed = true; Heading.Text = "NPC Chat 제거 완료";
            Status.Text = "시작 메뉴와 Windows 설치 목록에서 제거했어요.\n"
                + (data ? "대화 기록·설정 보존: " + scope.Data + "\n" : "대화 기록·설정·백업을 삭제했어요.\n")
                + (model ? "모델 보존: " + Path.GetDirectoryName(WindowsInstall.RetainedModel(root, release)) : "이번 설치의 모델을 삭제했어요.")
                + "\n설치 목록에 없는 개인 파일은 삭제하지 않습니다.";
            RemoveButton.Visibility = Visibility.Collapsed; CloseButton.Content = "닫기";
        } catch (Exception ex) {
            Status.Text = "제거를 완료하지 못했어요. 앱을 완전히 종료하고 다시 시도해 주세요.\n" + ex.Message;
            RemoveButton.IsEnabled = true; KeepData.IsEnabled = true; KeepModel.IsEnabled = true;
        } finally { running = false; CloseButton.IsEnabled = true; }
    }
    internal async Task Smoke(string output)
    {
        if (Directory.Exists(output)) throw new IOException("검증에는 새 출력 폴더를 사용하세요.");
        Directory.CreateDirectory(output); Show(); await Task.Delay(200);
        Capture(Path.Combine(output, "uninstall-options.png"));
        // Smoke never opts into deleting the user's shared data.
        await RemoveAsync();
        Capture(Path.Combine(output, "uninstall-result.png"));
        File.WriteAllText(Path.Combine(output, "result.json"), System.Text.Json.JsonSerializer.Serialize(new {passed=completed,topmost=Topmost,keepData=true,keepModel=true}));
        if (!completed) throw new IOException(Status.Text);
        Close();
    }
    void Capture(string file)
    {
        UpdateLayout(); var b = new RenderTargetBitmap((int)ActualWidth,(int)ActualHeight,96,96,PixelFormats.Pbgra32); b.Render(this);
        var p = new PngBitmapEncoder(); p.Frames.Add(BitmapFrame.Create(b)); using var s = File.Create(file); p.Save(s);
    }
}
