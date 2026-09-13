using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Animation;
using Windows.UI.ViewManagement;

namespace Sidey.App.Controls;

public sealed partial class SkeletonBar : UserControl
{
    internal bool IsPulseRunning => _pulse.GetCurrentState() == ClockState.Active;

    private static readonly UISettings s_userInterfaceSettings = new();
    private readonly Storyboard _pulse = new();
    private readonly List<(UIElement Element, long Token)> _ancestorVisibilitySubscriptions = [];
    private bool _isPulsing;

    public SkeletonBar()
    {
        InitializeComponent();
        var opacity = new DoubleAnimation
        {
            From = 0.55,
            To = 0.85,
            Duration = TimeSpan.FromMilliseconds(850),
            AutoReverse = true,
            RepeatBehavior = RepeatBehavior.Forever,
        };
        Storyboard.SetTarget(opacity, this);
        Storyboard.SetTargetProperty(opacity, "Opacity");
        _pulse.Children.Add(opacity);

        Loaded += OnLoaded;
        Unloaded += OnUnloaded;
        _ = RegisterPropertyChangedCallback(
            VisibilityProperty,
            (_, _) => UpdateAnimation());
    }

    private void OnLoaded(object sender, RoutedEventArgs args)
    {
        _ = sender;
        _ = args;
        ObserveAncestorVisibility();
        UpdateAnimation();
    }

    private void OnUnloaded(object sender, RoutedEventArgs args)
    {
        _ = sender;
        _ = args;
        StopAnimation();
        ClearAncestorVisibilitySubscriptions();
    }

    private void UpdateAnimation()
    {
        bool shouldPulse = IsLoaded
            && IsVisibleInTree()
            && s_userInterfaceSettings.AnimationsEnabled;
        if (!shouldPulse)
        {
            StopAnimation();
        }
        else if (!_isPulsing)
        {
            _pulse.Begin();
            _isPulsing = true;
        }
    }

    private void StopAnimation()
    {
        _pulse.Stop();
        _isPulsing = false;
        Opacity = 0.7;
    }

    private bool IsVisibleInTree()
    {
        for (DependencyObject? current = this; current is not null; current = VisualTreeHelper.GetParent(current))
        {
            if (current is UIElement { Visibility: Visibility.Collapsed })
                return false;
        }
        return true;
    }

    private void ObserveAncestorVisibility()
    {
        ClearAncestorVisibilitySubscriptions();
        for (DependencyObject? current = VisualTreeHelper.GetParent(this);
            current is not null;
            current = VisualTreeHelper.GetParent(current))
        {
            if (current is UIElement element)
            {
                long token = element.RegisterPropertyChangedCallback(
                    VisibilityProperty, (_, _) => UpdateAnimation());
                _ancestorVisibilitySubscriptions.Add((element, token));
            }
        }
    }

    private void ClearAncestorVisibilitySubscriptions()
    {
        foreach ((UIElement element, long token) in _ancestorVisibilitySubscriptions)
            element.UnregisterPropertyChangedCallback(VisibilityProperty, token);
        _ancestorVisibilitySubscriptions.Clear();
    }
}
