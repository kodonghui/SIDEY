using Sidey.Core.Domain;
using Sidey.Core.Overlay;

namespace Sidey.Core.Tests;

public sealed class CharacterInteractionTests
{
    [Fact]
    public void SingleRightClickWaitsForTheSystemIntervalAndDoubleClickCancelsIt()
    {
        var input = new CharacterRightClickState();
        Assert.False(input.Press(false, 10, 0.5));
        Assert.False(input.TakeSingle(10.49));
        Assert.True(input.TakeSingle(10.5));
        Assert.False(input.TakeSingle(11));
        input.Press(false, 12, 0.5);
        Assert.True(input.Press(true, 12.3, 0.5));
        Assert.False(input.TakeSingle(13));
        input.Press(false, 14, 0.5);
        input.Cancel();
        Assert.False(input.TakeSingle(15));
    }

    [Fact]
    public void SavedTreePauseAffectsOnlyTheCurrentUsersTree()
    {
        var tree = new PixelWorldMember(Guid.Parse("f351bd76-1e79-4ccd-92f5-5d58e8c62fb9"),
            "Tree", "pixel_tree", PresenceState.Online, false, true);
        Assert.True(PixelMovementPolicy.IsTreePaused(tree, true));
        Assert.False(PixelMovementPolicy.IsTreePaused(tree, false));
        Assert.False(PixelMovementPolicy.IsTreePaused(tree with { IsCurrentUser = false }, true));
        Assert.False(PixelMovementPolicy.IsTreePaused(tree with { CharacterId = "pixel_otter" }, true));
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(0.079, 0)]
    [InlineData(0.08, 1)]
    [InlineData(0.18, 2)]
    [InlineData(0.459, 2)]
    [InlineData(0.46, 3)]
    [InlineData(0.58, 3)]
    public void DujjonkuKeepsTheStretchFrameVisibleForItsApprovedDuration(double elapsed, int expectedFrame)
    {
        Assert.Equal(0.58, CharacterImpactTiming.Duration("throwable_dujjonku"));
        Assert.Equal(expectedFrame, CharacterImpactTiming.Frame("throwable_dujjonku", elapsed));
        Assert.Equal(0.24, CharacterImpactTiming.Duration("throwable_banana"));
        Assert.Equal(2, CharacterImpactTiming.Frame("throwable_banana", 0.12));
    }
}
