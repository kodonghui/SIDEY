import Foundation

/// Private client extension. The server still validates membership, cooldowns and equipment.
struct PlayfulEventTag: Equatable, Sendable {
    let kind: UInt8
    let skin: UInt8

    enum Channel { case pulse, projectile }

    static func decode(_ id: UUID, channel: Channel? = nil) -> PlayfulEventTag? {
        let text = id.uuidString.lowercased()
        guard text.hasPrefix("c07e"), "89ab".contains(text[text.index(text.startIndex, offsetBy: 19)]), text[text.index(text.startIndex, offsetBy: 14)] == "4",
              let kind = UInt8(text.dropFirst(4).prefix(2), radix: 16), (1...5).contains(kind),
              let skin = UInt8(text.dropFirst(6).prefix(2), radix: 16), skin <= 9 else { return nil }
        if channel == .pulse && !(3...4).contains(kind) { return nil }
        if channel == .projectile && ![1, 2, 5].contains(kind) { return nil }
        return PlayfulEventTag(kind: kind, skin: skin)
    }

    static func make(kind: UInt8, skin: UInt8) -> UUID {
        precondition((1...5).contains(kind) && skin <= 9)
        return UUID(uuidString: String(format: "c07e%02x%02x", kind, skin) + UUID().uuidString.dropFirst(8))!
    }

    var objectID: String? {
        switch kind { case 1: return "personal_poop"; case 2: return "personal_missile"; case 5: return "personal_air_pang"; default: return nil }
    }
}


struct PlayfulFireworkLayout {
    let rise: CGFloat
    let radius: CGFloat

    static func make(origin: CGPoint, bounds: CGSize) -> PlayfulFireworkLayout? {
        let vertical = bounds.height - origin.y - 8
        let horizontal = min(origin.x - 4, bounds.width - origin.x - 4)
        guard vertical > 8, horizontal > 2, origin.y >= 0 else { return nil }
        let rise = min(320, vertical * 0.55)
        let lowerEdgeRadius = max(0, (origin.y + rise - 4) / 1.5)
        let radius = min(144, min(vertical - rise, min(horizontal, lowerEdgeRadius)))
        return PlayfulFireworkLayout(rise: rise, radius: radius)
    }
}


/// Stable cross-platform wire IDs. Custom files never acquire a shared skin ID.
enum PlayfulSkinCatalog {
    static let names = ["default", "pepe", "agumon", "gabumon", "tentomon", "palmon", "gomamon", "biyomon", "patamon", "gatomon"]
    static func wireID(for name: String) -> UInt8 {
        guard let index = names.firstIndex(of: name) else { return 0 }
        return UInt8(index)
    }
    static func name(for wireID: UInt8) -> String {
        Int(wireID) < names.count ? names[Int(wireID)] : "default"
    }
}

/// Keep larger personal effects inside the transparent overlay's viewport.
enum PlayfulEffectLayout {
    static func center(_ point: CGPoint, extent: CGFloat, bounds: CGSize) -> CGPoint {
        let insetX = min(extent / 2, max(0, bounds.width / 2))
        let insetY = min(extent / 2, max(0, bounds.height / 2))
        return CGPoint(x: min(max(point.x, insetX), max(insetX, bounds.width - insetX)),
                       y: min(max(point.y, insetY), max(insetY, bounds.height - insetY)))
    }
}
