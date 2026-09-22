import Foundation

/// Private client extension. The server still validates membership, cooldowns and equipment.
struct PlayfulEventTag: Equatable, Sendable {
    let kind: UInt8
    let skin: UInt8

    enum Channel { case pulse, projectile }

    static func decode(_ id: UUID, channel: Channel? = nil) -> PlayfulEventTag? {
        let text = id.uuidString.lowercased()
        guard text.hasPrefix("c07e"), "89ab".contains(text[text.index(text.startIndex, offsetBy: 19)]), text[text.index(text.startIndex, offsetBy: 14)] == "4",
              let kind = UInt8(text.dropFirst(4).prefix(2), radix: 16), (1...4).contains(kind),
              let skin = UInt8(text.dropFirst(6).prefix(2), radix: 16), skin <= 1 else { return nil }
        if channel == .pulse && !(3...4).contains(kind) { return nil }
        if channel == .projectile && !(1...2).contains(kind) { return nil }
        return PlayfulEventTag(kind: kind, skin: skin)
    }

    static func make(kind: UInt8, skin: UInt8) -> UUID {
        precondition((1...4).contains(kind) && skin <= 1)
        return UUID(uuidString: String(format: "c07e%02x%02x", kind, skin) + UUID().uuidString.dropFirst(8))!
    }

    var objectID: String? {
        switch kind { case 1: return "personal_poop"; case 2: return "personal_missile"; default: return nil }
    }
}


struct PlayfulFireworkLayout {
    let rise: CGFloat
    let radius: CGFloat

    static func make(origin: CGPoint, bounds: CGSize) -> PlayfulFireworkLayout? {
        let vertical = bounds.height - origin.y - 8
        let horizontal = min(origin.x - 4, bounds.width - origin.x - 4)
        guard vertical > 8, horizontal > 2, origin.y >= 0 else { return nil }
        let rise = min(220, vertical * 0.65)
        let radius = min(72, min(vertical - rise, horizontal))
        return PlayfulFireworkLayout(rise: rise, radius: radius)
    }
}

