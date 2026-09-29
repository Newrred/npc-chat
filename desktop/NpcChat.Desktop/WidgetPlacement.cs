using System;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using Forms = System.Windows.Forms;

namespace NpcChat.Desktop;

internal static class WidgetPlacement
{
    [StructLayout(LayoutKind.Sequential)] internal struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr window, out Rect rect);
    [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr window, IntPtr after, int x, int y, int w, int h, uint flags);
    private static WorkArea Area(Forms.Screen screen) => new(screen.DeviceName, screen.WorkingArea.X,
        screen.WorkingArea.Y, screen.WorkingArea.Width, screen.WorkingArea.Height);
    public static WorkArea[] Areas() => Forms.Screen.AllScreens.OrderByDescending(s => s.Primary).Select(Area).ToArray();
    public static WidgetState Capture(Window window, WidgetState state)
    {
        var handle = new WindowInteropHelper(window).Handle;
        if (handle == IntPtr.Zero || !GetWindowRect(handle, out var r)) return state;
        var a = Area(Forms.Screen.FromHandle(handle));
        return (state with { Monitor = a.Id, LegacyLeft = null, LegacyTop = null,
            X = (r.Left - a.X) / (double)Math.Max(1, a.Width - (r.Right - r.Left)),
            Y = (r.Top - a.Y) / (double)Math.Max(1, a.Height - (r.Bottom - r.Top)) }).Validated();
    }
    public static void Restore(Window window, WidgetState state)
    {
        var handle = new WindowInteropHelper(window).Handle;
        if (handle == IntPtr.Zero || !GetWindowRect(handle, out var r)) return;
        if (state.LegacyLeft is double left && state.LegacyTop is double top && double.IsFinite(left) && double.IsFinite(top)) {
            window.Left = left; window.Top = top;
            Restore(window, Capture(window, state));
            return;
        }
        var a = WidgetState.Select(state.Monitor, Areas());
        var p = state.Position(a, r.Right - r.Left, r.Bottom - r.Top);
        // Physical coordinates: WPF handles WM_DPICHANGED; do not mix virtual desktop pixels with DIPs.
        SetWindowPos(handle, IntPtr.Zero, p.X, p.Y, 0, 0, 0x0015); // no size, z-order or activation
    }
}
