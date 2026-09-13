using System.Collections.Concurrent;
using System.Runtime.InteropServices;

namespace Sidey.Platform.Windows.Tests;

public sealed class NativeRightClickTests
{
    [Fact]
    public void NativeRightButtonDownAndDoubleClickProduceDistinctGesturesWithoutAnExtraRelease()
    {
        var gestures = new ConcurrentQueue<bool>();
        using var windows = NativeOverlayWindowThread.Start(
            new NativePixelRect(-10000, -10000, 1, 1),
            new NativePixelRect(-10000, -10000, 1, 1),
            hotspotRightClicked: gestures.Enqueue);
        foreach (uint message in new uint[] { 0x0204, 0x0205, 0x0206, 0x0205 })
        {
            Assert.NotEqual(nint.Zero, SendMessageTimeout(windows.HotspotWindowHandle,
                message, 0, 0, 2, 1000, out _));
        }
        Assert.Equal<bool>([false, true], gestures);
    }

    [DllImport("user32.dll", EntryPoint = "SendMessageTimeoutW", SetLastError = true)]
    private static extern nint SendMessageTimeout(nint window, uint message, nuint wParam,
        nint lParam, uint flags, uint timeoutMilliseconds, out nuint result);
}
