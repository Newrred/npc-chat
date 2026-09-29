using System.Windows;
using System.Windows.Controls;

namespace NpcChat.Desktop;

public partial class ChatShell : UserControl
{
    public ChatShell() { InitializeComponent(); }
    private void Minimize(object sender, RoutedEventArgs e) => Window.GetWindow(this).WindowState = WindowState.Minimized;
    private void ToggleMaximize(object sender, RoutedEventArgs e)
    {
        var window = Window.GetWindow(this);
        window.WindowState = window.WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;
    }
    private void HideChat(object sender, RoutedEventArgs e) => Window.GetWindow(this).Close();
}
