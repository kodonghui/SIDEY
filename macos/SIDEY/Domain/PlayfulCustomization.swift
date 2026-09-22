import AppKit
import SpriteKit
import UniformTypeIdentifiers
import ImageIO

@MainActor
final class PlayfulCustomization {
    static let shared = PlayfulCustomization()
    static let throwKey = "personal.playful.throw"
    static let skinKey = "personal.playful.skin"
    private var cachedTextures: [String: SKTexture] = [:]
    private var roomSkins: [UUID: [UUID: UInt8]] = [:]
    var wireSkin: UInt8 { UserDefaults.standard.string(forKey: Self.skinKey) == "pepe" ? 1 : 0 }
    var throwKind: UInt8 { Self.validatedThrowKind(UserDefaults.standard.integer(forKey: Self.throwKey)) }
    nonisolated static func validatedThrowKind(_ value: Int) -> UInt8 {
        (1...2).contains(value) ? UInt8(value) : 0
    }

    func remember(_ eventID: UUID, roomID: UUID, userID: UUID, channel: PlayfulEventTag.Channel) {
        guard let tag = PlayfulEventTag.decode(eventID, channel: channel) else { return }
        // Do not accumulate former rooms or retain cross-room identity state.
        roomSkins = [roomID: roomSkins[roomID] ?? [:]]
        roomSkins[roomID, default: [:]][userID] = tag.skin
    }

    func characterTexture(roomID: UUID?, member: PixelWorldMember) -> SKTexture? {
        let selection = member.isCurrentUser
            ? UserDefaults.standard.string(forKey: Self.skinKey) ?? "default"
            : ((roomID.flatMap { roomSkins[$0]?[member.id] } ?? 0) == 1 ? "pepe" : "default")
        guard selection != "default" else { return nil }
        if let cached = cachedTextures[selection] { return cached }
        let url: URL?
        if selection == "custom" { url = try? customURL() }
        else {
            url = Bundle.main.url(forResource: "pepe", withExtension: "png", subdirectory: "PersonalCharacters")
                ?? Bundle.main.url(forResource: "pepe", withExtension: "png")
        }
        guard let url, let image = NSImage(contentsOf: url) else { return nil }
        let texture = SKTexture(image: image)
        texture.filteringMode = .nearest
        cachedTextures[selection] = texture
        return texture
    }

    private func customURL() throws -> URL {
        let directory = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                   appropriateFor: nil, create: true)
            .appendingPathComponent("SIDEY/PersonalCharacters", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory.appendingPathComponent("custom.png")
    }

    func importPNG() throws -> Bool {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.png]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        guard panel.runModal() == .OK, let url = panel.url else { return false }
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
        guard size > 0, size <= 4 * 1024 * 1024 else { throw ImportError.invalidImage }
        let data = try Data(contentsOf: url)
        guard data.starts(with: [137, 80, 78, 71, 13, 10, 26, 10]),
              let source = CGImageSourceCreateWithData(data as CFData, [kCGImageSourceShouldCache: false] as CFDictionary),
              CGImageSourceGetCount(source) == 1,
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = properties[kCGImagePropertyPixelWidth] as? Int,
              let height = properties[kCGImagePropertyPixelHeight] as? Int,
              (1...1024).contains(width), (1...1024).contains(height),
              let bitmap = NSBitmapImageRep(data: data),
              let png = bitmap.representation(using: .png, properties: [:]) else { throw ImportError.invalidImage }
        try png.write(to: customURL(), options: .atomic)
        cachedTextures.removeValue(forKey: "custom")
        UserDefaults.standard.set("custom", forKey: Self.skinKey)
        return true
    }

    enum ImportError: LocalizedError {
        case invalidImage
        var errorDescription: String? { "4MB 이하, 가로·세로 1024px 이하의 PNG를 선택해 주세요." }
    }

    func projectileTexture(kind: UInt8) -> SKTexture {
        let key = "projectile-\(kind)"
        if let texture = cachedTextures[key] { return texture }
        let image = NSImage(size: NSSize(width: 24, height: 24))
        image.lockFocus()
        NSGraphicsContext.current?.imageInterpolation = .none
        if kind == 1 {
            NSColor.brown.setFill()
            for rect in [NSRect(x: 3, y: 3, width: 18, height: 6), NSRect(x: 6, y: 9, width: 12, height: 5),
                         NSRect(x: 9, y: 14, width: 6, height: 5), NSRect(x: 11, y: 19, width: 3, height: 2)] {
                rect.fill()
            }
            NSColor.white.setFill()
            NSRect(x: 7, y: 7, width: 3, height: 3).fill()
            NSRect(x: 14, y: 7, width: 3, height: 3).fill()
            NSColor.black.setFill()
            NSRect(x: 8, y: 7, width: 1, height: 2).fill()
            NSRect(x: 15, y: 7, width: 1, height: 2).fill()
        } else {
            NSColor.systemOrange.setFill()
            NSRect(x: 0, y: 10, width: 7, height: 4).fill()
            NSColor.systemRed.setFill()
            NSRect(x: 5, y: 6, width: 4, height: 12).fill()
            NSRect(x: 18, y: 9, width: 4, height: 6).fill()
            NSColor.lightGray.setFill()
            NSRect(x: 7, y: 9, width: 12, height: 6).fill()
        }
        image.unlockFocus()
        let texture = SKTexture(image: image)
        texture.filteringMode = .nearest
        cachedTextures[key] = texture
        return texture
    }
}
