import XCTest
#if APP_STORE
@testable import SIDEYAppStore
#else
@testable import SIDEY
#endif

final class PlayfulCustomizationTests: XCTestCase {
    func testWindowsCompatibleEventVectorsDecodeWithoutChangingActorOrEquipment() {
        let room = UUID(), actor = UUID(), target = UUID()
        let event = CharacterThrowEvent(
            id: UUID(uuidString: "c07e0201-1234-4567-89ab-0123456789ab")!, roomID: room,
            actorUserID: actor, targetUserID: target, sourceCharacterID: "pixel_hamster",
            throwableID: "patch_soft_ball")
        XCTAssertEqual(event.throwableID, "personal_missile")
        XCTAssertEqual(event.actorUserID, actor)
        XCTAssertEqual(event.targetUserID, target)
        XCTAssertEqual(event.roomID, room)
        XCTAssertEqual(PlayfulEventTag.decode(event.id)?.skin, 1)
    }

    func testUnknownOrInvalidMarkersPreserveNormalThrowable() {
        for text in ["c07e0000-1234-4567-89ab-0123456789ab", "c07e010a-1234-4567-89ab-0123456789ab",
                     "c07e0100-1234-1567-89ab-0123456789ab", "c07e0100-1234-4567-09ab-0123456789ab",
                     "c07f0100-1234-4567-89ab-0123456789ab"] {
            let id = UUID(uuidString: text)!
            XCTAssertNil(PlayfulEventTag.decode(id))
            let event = CharacterThrowEvent(id: id, roomID: UUID(), actorUserID: UUID(), targetUserID: UUID(),
                                            sourceCharacterID: "pixel_hamster", throwableID: "patch_soft_ball")
            XCTAssertEqual(event.throwableID, "patch_soft_ball")
        }
    }

    func testOtherChannelMarkersFallBackAndCorruptPreferencesCannotTrap() {
        let projectile = UUID(uuidString: "c07e0101-1234-4567-89ab-0123456789ab")!
        let pulse = UUID(uuidString: "c07e0301-1234-4567-89ab-0123456789ab")!
        XCTAssertNil(PlayfulEventTag.decode(projectile, channel: .pulse))
        XCTAssertNil(PlayfulEventTag.decode(pulse, channel: .projectile))
        XCTAssertNotNil(PlayfulEventTag.decode(projectile, channel: .projectile))
        XCTAssertNotNil(PlayfulEventTag.decode(pulse, channel: .pulse))
        for value in [Int.min, -1, 0, 3, 256, Int.max] {
            XCTAssertEqual(PlayfulCustomization.validatedThrowKind(value), 0)
        }
        XCTAssertEqual(PlayfulCustomization.validatedThrowKind(1), 1)
        XCTAssertEqual(PlayfulCustomization.validatedThrowKind(2), 2)
        XCTAssertEqual(PlayfulCustomization.validatedThrowKind(5), 5)
    }

    func testAirPangAndEverySharedSkinUseWindowsCompatibleIDs() throws {
        let air = UUID(uuidString: "c07e0509-1234-4567-89ab-0123456789ab")!
        let tag = try XCTUnwrap(PlayfulEventTag.decode(air, channel: .projectile))
        XCTAssertEqual(tag.objectID, "personal_air_pang")
        XCTAssertEqual(PlayfulSkinCatalog.name(for: tag.skin), "gatomon")
        XCTAssertNil(PlayfulEventTag.decode(air, channel: .pulse))
        let expected = ["default", "pepe", "agumon", "gabumon", "tentomon", "palmon", "gomamon", "biyomon", "patamon", "gatomon"]
        for (id, name) in expected.enumerated() {
            XCTAssertEqual(PlayfulSkinCatalog.wireID(for: name), UInt8(id))
            XCTAssertEqual(PlayfulSkinCatalog.name(for: UInt8(id)), name)
        }
        XCTAssertEqual(PlayfulSkinCatalog.wireID(for: "custom"), 0)
        XCTAssertEqual(PlayfulSkinCatalog.wireID(for: "unknown"), 0)
        XCTAssertEqual(PlayfulSkinCatalog.name(for: 255), "default")
    }

    func testLargeEffectsStayWithinViewportAtEveryCorner() {
        let bounds = CGSize(width: 500, height: 400)
        for point in [CGPoint(x: -20, y: -20), CGPoint(x: 520, y: 420), CGPoint(x: 250, y: 200)] {
            let center = PlayfulEffectLayout.center(point, extent: 96, bounds: bounds)
            XCTAssertGreaterThanOrEqual(center.x - 48, 0)
            XCTAssertGreaterThanOrEqual(center.y - 48, 0)
            XCTAssertLessThanOrEqual(center.x + 48, bounds.width)
            XCTAssertLessThanOrEqual(center.y + 48, bounds.height)
        }
        XCTAssertEqual(PlayfulEffectLayout.center(.zero, extent: 96, bounds: CGSize(width: 20, height: 20)), CGPoint(x: 10, y: 10))
        let layout = PlayfulFireworkLayout.make(origin: CGPoint(x: 800, y: 24), bounds: CGSize(width: 1600, height: 900))
        XCTAssertEqual(layout?.radius, 144)
    }

    func testFireworkMovesScreenUpAndKeepsBurstWithinViewport() throws {
        let bounds = CGSize(width: 500, height: 400)
        for origin in [CGPoint(x: 250, y: 24), CGPoint(x: 30, y: 350), CGPoint(x: 470, y: 200)] {
            let layout = try XCTUnwrap(PlayfulFireworkLayout.make(origin: origin, bounds: bounds))
            XCTAssertGreaterThan(layout.rise, 0)
            XCTAssertLessThan(origin.y + layout.rise + layout.radius, bounds.height)
            XCTAssertGreaterThanOrEqual(origin.y + layout.rise - layout.radius - min(18, layout.radius / 2), 4)
            XCTAssertGreaterThanOrEqual(origin.x - layout.radius, 0)
            XCTAssertLessThanOrEqual(origin.x + layout.radius, bounds.width)
        }
        XCTAssertNil(PlayfulFireworkLayout.make(origin: CGPoint(x: 250, y: 399), bounds: bounds))
    }

    func testEverySupportedKindRoundTripsAsDistinctUUIDVersion4() {
        for kind: UInt8 in 1...5 {
            for skin: UInt8 in 0...9 {
                let first = PlayfulEventTag.make(kind: kind, skin: skin)
                let second = PlayfulEventTag.make(kind: kind, skin: skin)
                XCTAssertNotEqual(first, second)
                XCTAssertEqual(PlayfulEventTag.decode(first), PlayfulEventTag(kind: kind, skin: skin))
            }
        }
    }
}
