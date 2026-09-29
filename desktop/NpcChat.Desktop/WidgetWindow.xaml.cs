using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.Win32;

namespace NpcChat.Desktop;

public partial class WidgetWindow : Window
{
    private readonly App owner;
    private WidgetState state;
    private readonly DispatcherTimer saveTimer = new() { Interval = TimeSpan.FromMilliseconds(350) };
    private bool placed;
    private bool faceDragged;
    private Point faceStart;
    public string? PendingCharacter { get; private set; }
    public WidgetState Preferences => state;
    private string StatePath => Path.Combine(owner.DataDirectory, "widget.json");
    public WidgetWindow(App app)
    {
        InitializeComponent(); owner = app; state = WidgetState.Load(StatePath);
        ApplySize();
        SetFace(Path.Combine(app.Root, "frontend/faces/neutral.png"), "유이");
        Loaded += (_, _) => {
            WidgetPlacement.Restore(this, state); placed = true;
            Dispatcher.BeginInvoke(() => WidgetPlacement.Restore(this, state), DispatcherPriority.ContextIdle);
        };
        LocationChanged += (_, _) => ScheduleSave();
        saveTimer.Tick += (_, _) => { saveTimer.Stop(); SavePreferences(); };
        SystemEvents.DisplaySettingsChanged += DisplaysChanged;
        Closing += (_, e) => { if (!app.Exiting) { e.Cancel = true; Hide(); } };
        Closed += (_, _) => { saveTimer.Stop(); SavePreferences(); SystemEvents.DisplaySettingsChanged -= DisplaysChanged; };
    }
    private void DisplaysChanged(object? sender, EventArgs e) => Dispatcher.BeginInvoke(() => {
        WidgetPlacement.Restore(this, state); ScheduleSave();
    });
    protected override void OnDpiChanged(DpiScale oldDpi, DpiScale newDpi)
    {
        base.OnDpiChanged(oldDpi, newDpi);
        Dispatcher.BeginInvoke(() => { WidgetPlacement.Restore(this, WidgetPlacement.Capture(this, state)); ScheduleSave(); });
    }
    private void ApplySize()
    {
        state = state.Validated();
        WidgetCanvas.Width = state.Compact ? 150 : 190;
        WidgetCanvas.Height = state.Compact ? 180 : 282;
        Width = WidgetCanvas.Width * state.Scale; Height = WidgetCanvas.Height * state.Scale;
        FullCard.Visibility = state.Compact ? Visibility.Collapsed : Visibility.Visible;
        CompactCard.Visibility = state.Compact ? Visibility.Visible : Visibility.Collapsed;
        Topmost = state.Topmost;
    }
    public void SetPreferences(double scale, bool compact, bool topmost)
    {
        state = WidgetPlacement.Capture(this, state) with { Scale = scale, Compact = compact, Topmost = topmost };
        ApplySize(); UpdateLayout(); WidgetPlacement.Restore(this, state); SavePreferences();
    }
    private void ScheduleSave() { if (!placed) return; saveTimer.Stop(); saveTimer.Start(); }
    public void SavePreferences()
    {
        if (!placed) return;
        state = WidgetPlacement.Capture(this, state);
        try { state.Save(StatePath); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { Status.ToolTip = "위젯 설정을 저장하지 못했어요. 저장 폴더 권한을 확인하세요."; }
    }
    public void SetFace(string path, string name)
    {
        if (!File.Exists(path)) return;
        var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad;
        image.UriSource = new Uri(path); image.EndInit(); image.Freeze(); Portrait.Source = image;
        CharacterName.Text = name;
    }
    public void NotifyReply(string character)
    {
        PendingCharacter = character; ReplyBadge.Visibility = Visibility.Visible;
        CompactReply.Visibility = Visibility.Visible; ChatButton.Content = "새 답장 확인  ↗";
    }
    public void ClearReply()
    {
        PendingCharacter = null; ReplyBadge.Visibility = Visibility.Collapsed;
        CompactReply.Visibility = Visibility.Collapsed; ChatButton.Content = "대화하기  ↗";
    }
    private void DragHeader(object sender, MouseButtonEventArgs e)
    {
        var source = e.OriginalSource as DependencyObject;
        while (source != null) {
            if (source is ButtonBase) return;
            source = VisualTreeHelper.GetParent(source);
        }
        if (e.ButtonState == MouseButtonState.Pressed) { DragMove(); SavePreferences(); }
    }
    private void FaceDown(object sender, MouseButtonEventArgs e) { faceStart = e.GetPosition(this); faceDragged = false; }
    private void FaceMove(object sender, MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed || faceDragged || (e.GetPosition(this) - faceStart).Length < 5) return;
        faceDragged = true; DragMove(); SavePreferences();
    }
    private void FaceUp(object sender, MouseButtonEventArgs e) { if (!faceDragged) owner.ShowChat(); }
    private void ResizeWidget(object sender, DragDeltaEventArgs e)
    {
        var change = Math.Abs(e.HorizontalChange) > Math.Abs(e.VerticalChange) ? e.HorizontalChange / WidgetCanvas.Width : e.VerticalChange / WidgetCanvas.Height;
        state = state with { Scale = Math.Clamp(state.Scale + change, .75, 1.6) }; ApplySize();
    }
    private void ResizeCompleted(object sender, DragCompletedEventArgs e)
    {
        state = WidgetPlacement.Capture(this, state); WidgetPlacement.Restore(this, state); SavePreferences();
    }
    private void OpenChat(object sender, RoutedEventArgs e) => owner.ShowChat();
    private void OpenMenu(object sender, RoutedEventArgs e) => ShowMenu((FrameworkElement)sender);
    private void RightMenu(object sender, MouseButtonEventArgs e) { ShowMenu(this); e.Handled = true; }
    private void ShowMenu(FrameworkElement anchor)
    {
        var menu = new ContextMenu();
        void Add(string title, Action action) { var item = new MenuItem { Header = title }; item.Click += (_, _) => action(); menu.Items.Add(item); }
        Add("채팅 열기", owner.ShowChat);
        Add("실행 상태 / 문제 해결", owner.ShowDiagnostics);
        foreach (var size in new[] { ("작게", .8), ("보통", 1.0), ("크게", 1.3) })
            Add("크기 · " + size.Item1, () => SetPreferences(size.Item2, state.Compact, state.Topmost));
        var compact = new MenuItem { Header = "얼굴만 보기", IsCheckable = true, IsChecked = state.Compact };
        compact.Click += (_, _) => SetPreferences(state.Scale, compact.IsChecked, state.Topmost); menu.Items.Add(compact);
        var pin = new MenuItem { Header = "항상 위에 표시", IsCheckable = true, IsChecked = state.Topmost };
        pin.Click += (_, _) => SetPreferences(state.Scale, state.Compact, pin.IsChecked); menu.Items.Add(pin);
        Add("위젯 숨기기 (트레이에서 복원)", Hide);
        Add("화면 안으로 위치 복구", () => { state = state with { Monitor = "", X = .95, Y = .95 }; WidgetPlacement.Restore(this, state); SavePreferences(); });
        var quit = new MenuItem { Header = "완전히 종료" }; quit.Click += async (_, _) => await owner.Quit(); menu.Items.Add(quit);
        menu.PlacementTarget = anchor; menu.IsOpen = true;
    }
}
