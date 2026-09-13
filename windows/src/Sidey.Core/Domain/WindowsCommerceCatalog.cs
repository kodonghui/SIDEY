using System.Text.Json;

namespace Sidey.Core.Domain;

public static class WindowsCommerceCatalog
{
    public static IReadOnlyList<CommerceProduct> Products { get; } = LoadProducts();

    public static CommerceProduct? Find(string productId) =>
        Products.FirstOrDefault(product => StringComparer.Ordinal.Equals(product.Id, productId));

    public static CommerceProduct? KeepsakeFor(string characterId) =>
        Products.FirstOrDefault(product => product.Kind == CommerceProductKind.Throwable
            && product.RelatedCharacterProductId == Products.FirstOrDefault(character =>
                character.Kind == CommerceProductKind.Character && character.CharacterId == characterId)?.Id
            && product.RelatedCharacterProductId is not null);

    public static IReadOnlyList<CommerceProductState> LockedStates() =>
        [.. Products.Select(product => new CommerceProductState(
            product, GoogleConnected: false, CommercePurchaseState.Unavailable))];

    private static IReadOnlyList<CommerceProduct> LoadProducts()
    {
        using Stream stream = typeof(WindowsCommerceCatalog).Assembly.GetManifestResourceStream(
            "Sidey.Core.commerce-catalog.json")
            ?? throw new InvalidDataException("The bundled commerce catalog is missing.");
        using var document = JsonDocument.Parse(stream);
        return Array.AsReadOnly(document.RootElement.EnumerateArray().Select(entry =>
            new CommerceProduct(
                entry.GetProperty("id").GetString()!,
                OptionalString(entry, "character_id") ?? PixelCharacterCatalog.FallbackId,
                entry.GetProperty("entitlement").GetString()!,
                entry.GetProperty("sort_order").GetInt32(),
                entry.GetProperty("direct_price").GetInt32(),
                Enum.Parse<CommerceProductKind>(entry.GetProperty("kind").GetString()!, ignoreCase: true),
                entry.GetProperty("item_id").GetString(),
                OptionalString(entry, "render_asset_id"),
                OptionalString(entry, "related_character_product_id"))).ToArray());
    }

    private static string? OptionalString(JsonElement entry, string name) =>
        entry.TryGetProperty(name, out JsonElement value) ? value.GetString() : null;
}
