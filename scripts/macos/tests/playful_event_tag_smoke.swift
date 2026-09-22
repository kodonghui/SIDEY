// Standalone foundation-level smoke; this does not compile the macOS app.
// swiftc macos/SIDEY/Domain/PlayfulEventTag.swift scripts/macos/tests/playful_event_tag_smoke.swift -o /tmp/sidey-tag-smoke
import Foundation

@main
struct PlayfulEventTagSmoke {
    static func main() {
        let windowsVector = UUID(uuidString: "c07e0201-1234-4567-89ab-0123456789ab")!
        precondition(PlayfulEventTag.decode(windowsVector, channel: .projectile)?.objectID == "personal_missile")
        precondition(PlayfulEventTag.decode(windowsVector, channel: .projectile)?.skin == 1)
        precondition(PlayfulEventTag.decode(windowsVector, channel: .pulse) == nil)
        for kind: UInt8 in 1...5 {
            for skin: UInt8 in 0...9 {
                let first = PlayfulEventTag.make(kind: kind, skin: skin)
                precondition(PlayfulEventTag.decode(first) == PlayfulEventTag(kind: kind, skin: skin))
                precondition(first != PlayfulEventTag.make(kind: kind, skin: skin))
            }
        }
        for text in ["c07e0000-1234-4567-89ab-0123456789ab", "c07e010a-1234-4567-89ab-0123456789ab",
                     "c07e0100-1234-1567-89ab-0123456789ab", "c07e0100-1234-4567-09ab-0123456789ab"] {
            precondition(PlayfulEventTag.decode(UUID(uuidString: text)!) == nil)
        }
        let air = UUID(uuidString: "c07e0509-1234-4567-89ab-0123456789ab")!
        precondition(PlayfulEventTag.decode(air, channel: .projectile)?.objectID == "personal_air_pang")
        precondition(PlayfulEventTag.decode(air, channel: .pulse) == nil)
        for (id, name) in PlayfulSkinCatalog.names.enumerated() {
            precondition(PlayfulSkinCatalog.wireID(for: name) == UInt8(id))
            precondition(PlayfulSkinCatalog.name(for: UInt8(id)) == name)
        }
        precondition(PlayfulSkinCatalog.wireID(for: "custom") == 0)
        precondition(PlayfulSkinCatalog.name(for: 255) == "default")
        let bounds = CGSize(width: 500, height: 400)
        for point in [CGPoint(x: -20, y: -20), CGPoint(x: 520, y: 420), CGPoint(x: 250, y: 200)] {
            let center = PlayfulEffectLayout.center(point, extent: 96, bounds: bounds)
            precondition(center.x - 48 >= 0 && center.y - 48 >= 0)
            precondition(center.x + 48 <= bounds.width && center.y + 48 <= bounds.height)
        }
        for origin in [CGPoint(x: 250, y: 24), CGPoint(x: 30, y: 350), CGPoint(x: 470, y: 200)] {
            let layout = PlayfulFireworkLayout.make(origin: origin, bounds: bounds)!
            precondition(layout.rise > 0)
            precondition(origin.y + layout.rise + layout.radius < bounds.height)
            precondition(origin.y + layout.rise - layout.radius - min(18, layout.radius / 2) >= 4)
            precondition(origin.x - layout.radius >= 0 && origin.x + layout.radius <= bounds.width)
        }
        precondition(PlayfulFireworkLayout.make(origin: CGPoint(x: 250, y: 399), bounds: bounds) == nil)
        print("PASS: UUID codec vectors, strict fallback, channel filtering, fresh IDs, upward bounded firework geometry")
    }
}
