using Sidey.Core.Domain;

namespace Sidey.Core.Overlay;

public static class CharacterImpactTiming
{
    public static double Duration(string? objectId) =>
        CosmeticCatalog.ResolveThrowableAssetId(objectId) == "throwable_dujjonku" ? 0.58d : 0.24d;

    public static int Frame(string? objectId, double elapsedSeconds)
    {
        double elapsed = Math.Max(0d, elapsedSeconds);
        if (CosmeticCatalog.ResolveThrowableAssetId(objectId) == "throwable_dujjonku")
        {
            return elapsed < 0.08d ? 0 : elapsed < 0.18d ? 1 : elapsed < 0.46d ? 2 : 3;
        }
        return Math.Min(3, (int)(elapsed / 0.06d));
    }
}
