namespace Sidey.Core.Overlay;

/// <summary>The owner serializes access and cancels pending input when its scene changes.</summary>
public sealed class CharacterRightClickState
{
    private double? _singleDeadline;

    public bool Press(bool isDoubleClick, double nowSeconds, double doubleClickIntervalSeconds)
    {
        _singleDeadline = isDoubleClick ? null : nowSeconds + doubleClickIntervalSeconds;
        return isDoubleClick;
    }

    public bool TakeSingle(double nowSeconds)
    {
        if (_singleDeadline is not { } deadline || nowSeconds < deadline)
        {
            return false;
        }
        _singleDeadline = null;
        return true;
    }

    public void Cancel() => _singleDeadline = null;
}
