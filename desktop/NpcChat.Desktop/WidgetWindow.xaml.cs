using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media.Imaging;

namespace NpcChat.Desktop;

public partial class WidgetWindow : Window
{
    private readonly App owner;
    public WidgetWindow(App app)
    {
        InitializeComponent(); owner = app;
        Left = SystemParameters.WorkArea.Right - Width - 24;
        Top = SystemParameters.WorkArea.Bottom - Height - 24;
        try {
            var p = JsonSerializer.Deserialize<double[]>(File.ReadAllText(Path.Combine(app.DataDirectory, "widget.json")));
            if (p?.Length == 2 && double.IsFinite(p[0]) && double.IsFinite(p[1])) {
                Left = Math.Clamp(p[0], SystemParameters.WorkArea.Left, Math.Max(SystemParameters.WorkArea.Left, SystemParameters.WorkArea.Right - Width));
                Top = Math.Clamp(p[1], SystemParameters.WorkArea.Top, Math.Max(SystemParameters.WorkArea.Top, SystemParameters.WorkArea.Bottom - Height));
            }
        } catch (Exception e) when (e is IOException or JsonException) { }
        SetFace(Path.Combine(app.Root, "frontend/faces/neutral.png"), "유이");
        Closing += (_, e) => { if (!app.Exiting) { e.Cancel = true; Hide(); } };
    }
    public void SetFace(string path, string name)
    {
        if (!File.Exists(path)) return;
        var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad;
        image.UriSource = new Uri(path); image.EndInit(); image.Freeze(); Portrait.Source = image;
        CharacterName.Text = name;
    }
    private void DragHeader(object sender, MouseButtonEventArgs e)
    {
        if (e.OriginalSource is Button) return;
        if (e.ButtonState == MouseButtonState.Pressed) DragMove();
        try { File.WriteAllText(Path.Combine(owner.DataDirectory, "widget.json"), JsonSerializer.Serialize(new[] { Left, Top })); }
        catch (IOException) { }
    }
    private void OpenChat(object sender, RoutedEventArgs e) => owner.ShowChat();
    private void OpenMenu(object sender, RoutedEventArgs e)
    {
        var menu = new ContextMenu();
        var chat = new MenuItem { Header = "채팅 열기" }; chat.Click += (_, _) => owner.ShowChat();
        var pin = new MenuItem { Header = "항상 위에 표시", IsCheckable = true, IsChecked = Topmost }; pin.Click += (_, _) => Topmost = pin.IsChecked;
        var hide = new MenuItem { Header = "위젯 숨기기 (트레이에서 복원)" }; hide.Click += (_, _) => Hide();
        var quit = new MenuItem { Header = "완전히 종료" }; quit.Click += async (_, _) => await owner.Quit();
        var status = new MenuItem { Header = "실행 상태 / 문제 해결" }; status.Click += (_, _) => owner.ShowDiagnostics();
        menu.Items.Add(chat); menu.Items.Add(status); menu.Items.Add(pin); menu.Items.Add(hide); menu.Items.Add(new Separator()); menu.Items.Add(quit);
        menu.PlacementTarget = (Button)sender; menu.IsOpen = true;
    }
}
