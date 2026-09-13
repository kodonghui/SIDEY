namespace Sidey.Core.Domain;

public static class ImpactSoundCatalog
{
    public static IReadOnlyList<string> Ids { get; } = Array.AsReadOnly(
        new[] { "patch_soft_ball" }.Concat(WindowsCommerceCatalog.Products
            .Where(product => product.Kind == CommerceProductKind.Throwable)
            .Select(product => product.RenderAssetId!)).Distinct(StringComparer.Ordinal).ToArray());

    public static string Resolve(string characterId, string? equippedId) =>
        CosmeticCatalog.ResolveThrowableAssetId(equippedId);
}
