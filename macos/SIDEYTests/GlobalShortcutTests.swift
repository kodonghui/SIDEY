import AppKit
import Carbon.HIToolbox
import XCTest
#if APP_STORE
@testable import SIDEYAppStore
#else
@testable import SIDEY
#endif

@MainActor
final class GlobalShortcutTests: XCTestCase {
    func testValidationAcceptsTwoModifiersIncludingCommandOrControl() {
        XCTAssertNil(rejection(kVK_ANSI_K, [.control, .option]))
        XCTAssertNil(rejection(kVK_ANSI_1, [.shift, .command]))
        XCTAssertNil(rejection(kVK_Space, [.option, .shift, .command]))
        XCTAssertNil(rejection(kVK_F12, [.control, .shift]))
    }

    func testValidationRejectsMissingModifiersAndUnsupportedKeys() {
        XCTAssertEqual(rejection(kVK_ANSI_K, []), .modifiersRequired)
        XCTAssertEqual(rejection(kVK_ANSI_K, [.command]), .modifiersRequired)
        XCTAssertEqual(rejection(kVK_ANSI_K, [.option, .shift]), .modifiersRequired)
        XCTAssertEqual(rejection(kVK_ANSI_K, GlobalShortcutModifiers(rawValue: UInt32.max)), .modifiersRequired)
        XCTAssertEqual(rejection(kVK_Tab, [.control, .option]), .unsupportedKey)
        XCTAssertEqual(rejection(kVK_ANSI_Equal, [.control, .command]), .unsupportedKey)
        XCTAssertEqual(rejection(kVK_F13, [.control, .command]), .unsupportedKey)
    }

    func testValidationRejectsSystemCombinations() {
        XCTAssertEqual(rejection(kVK_Space, [.command]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_Space, [.option, .command]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_Space, [.control, .command]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_Space, [.control]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_Space, [.control, .option]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_Space, [.shift, .command]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_ANSI_3, [.shift, .command]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_ANSI_4, [.shift, .command]), .reservedBySystem)
        XCTAssertEqual(rejection(kVK_ANSI_5, [.shift, .command]), .reservedBySystem)
    }

    func testCombinationAssignedToAnotherActionIsRejected() {
        var assignments = GlobalShortcutAssignments()
        assignments.toggleOverlay = shortcut(kVK_ANSI_K, [.control, .option])

        XCTAssertEqual(
            rejection(kVK_ANSI_K, [.control, .option], for: .toggleComposer, among: assignments),
            .assigned(to: .toggleOverlay)
        )
        XCTAssertNil(rejection(kVK_ANSI_K, [.control, .option], for: .toggleOverlay, among: assignments))
    }

    func testDisplayStringUsesMacModifierOrder() {
        XCTAssertEqual(shortcut(kVK_ANSI_K, [.command, .shift, .option, .control]).displayString, "⌃⌥⇧⌘K")
        XCTAssertEqual(shortcut(kVK_Space, [.option, .control]).displayString, "⌃⌥Space")
        XCTAssertEqual(shortcut(kVK_ANSI_7, [.command, .shift]).displayString, "⇧⌘7")
        XCTAssertEqual(shortcut(kVK_F12, [.command, .control]).displayString, "⌃⌘F12")
    }

    func testEventModifierFlagsKeepOnlyShortcutModifiers() {
        let flags: NSEvent.ModifierFlags = [.command, .option, .capsLock, .function, .numericPad]
        let otherFlags: NSEvent.ModifierFlags = [.control, .shift]

        XCTAssertEqual(GlobalShortcutModifiers(flags), [.command, .option])
        XCTAssertEqual(GlobalShortcutModifiers(otherFlags), [.control, .shift])
    }

    func testShortcutPreferencesRoundTrip() throws {
        var value = AppPreferences.defaults
        value.globalShortcuts.toggleComposer = shortcut(kVK_ANSI_K, [.control, .option])
        value.globalShortcuts.toggleQuietMode = shortcut(kVK_F5, [.shift, .command])

        let data = try JSONEncoder().encode(value)
        let restored = try JSONDecoder().decode(AppPreferences.self, from: data)

        XCTAssertEqual(restored, value)
        XCTAssertNil(restored.globalShortcuts.toggleOverlay)
    }

    func testInvalidStoredShortcutsAreDroppedWithoutResettingOtherPreferences() throws {
        let valid = try encodedJSON(shortcut(kVK_ANSI_K, [.control, .option]))
        let singleModifier = try encodedJSON(shortcut(kVK_ANSI_M, [.command]))
        let json = #"{"schemaVersion":10,"quietModeEnabled":true,"nickname":"민지","globalShortcuts":{"toggleComposer":\#(valid),"toggleOverlay":\#(valid),"toggleQuietMode":\#(singleModifier)}}"#

        let value = try JSONDecoder().decode(AppPreferences.self, from: Data(json.utf8))

        XCTAssertEqual(value.globalShortcuts.toggleComposer, shortcut(kVK_ANSI_K, [.control, .option]))
        XCTAssertNil(value.globalShortcuts.toggleOverlay)
        XCTAssertNil(value.globalShortcuts.toggleQuietMode)
        XCTAssertTrue(value.quietModeEnabled)
        XCTAssertEqual(value.nickname, "민지")

        let damaged = #"{"quietModeEnabled":true,"nickname":"민지","globalShortcuts":{"toggleComposer":{"keyCode":"K"}}}"#
        let damagedValue = try JSONDecoder().decode(AppPreferences.self, from: Data(damaged.utf8))

        XCTAssertEqual(damagedValue.globalShortcuts, GlobalShortcutAssignments())
        XCTAssertTrue(damagedValue.quietModeEnabled)
        XCTAssertEqual(damagedValue.nickname, "민지")

        let wrongType = #"{"quietModeEnabled":true,"nickname":"민지","globalShortcuts":[1,2,3]}"#
        let wrongTypeValue = try JSONDecoder().decode(AppPreferences.self, from: Data(wrongType.utf8))

        XCTAssertEqual(wrongTypeValue.globalShortcuts, GlobalShortcutAssignments())
        XCTAssertTrue(wrongTypeValue.quietModeEnabled)
        XCTAssertEqual(wrongTypeValue.nickname, "민지")
    }

    func testStartRegistersSavedShortcutsAndMarksUnavailableOneWithoutDroppingIt() {
        let composer = shortcut(kVK_ANSI_K, [.control, .option])
        let quiet = shortcut(kVK_ANSI_Q, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.globalShortcuts.toggleComposer = composer
        preferences.globalShortcuts.toggleQuietMode = quiet
        let registrar = FakeGlobalHotKeyRegistrar()
        registrar.unavailable = [quiet]
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)

        controller.start()

        XCTAssertEqual(model.globalShortcutStatuses[.toggleComposer], .active)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleQuietMode], .unavailable)
        XCTAssertNil(model.globalShortcutStatuses[.toggleOverlay])
        XCTAssertEqual(model.preferences.globalShortcuts.toggleQuietMode, quiet)
        XCTAssertEqual(Set(registrar.active.keys), [composer])
        XCTAssertEqual(log.saves, 0)
    }

    func testRecordingPausesOwnShortcutsUntilCancelled() {
        let overlay = shortcut(kVK_ANSI_O, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.globalShortcuts.toggleOverlay = overlay
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)
        controller.start()

        controller.beginRecording(.toggleComposer)
        registrar.press(overlay)

        XCTAssertEqual(model.recordingGlobalShortcutAction, .toggleComposer)
        XCTAssertTrue(registrar.active.isEmpty)
        XCTAssertTrue(log.calls.isEmpty)

        controller.cancelRecording(.toggleOverlay)

        XCTAssertEqual(model.recordingGlobalShortcutAction, .toggleComposer)
        XCTAssertTrue(registrar.active.isEmpty)

        controller.cancelRecording(.toggleComposer)
        registrar.press(overlay)

        XCTAssertNil(model.recordingGlobalShortcutAction)
        XCTAssertEqual(Set(registrar.active.keys), [overlay])
        XCTAssertEqual(model.globalShortcutStatuses[.toggleOverlay], .active)
        XCTAssertEqual(log.calls, ["toggleOverlay"])
        XCTAssertEqual(log.saves, 0)
    }

    func testRecordedShortcutIsRegisteredAndSavedImmediately() {
        let combo = shortcut(kVK_ANSI_M, [.control, .command])
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(registrar: registrar, log: log)
        controller.start()

        controller.record(combo, for: .toggleComposer)

        XCTAssertNil(model.preferences.globalShortcuts.toggleComposer)

        controller.beginRecording(.toggleComposer)
        controller.record(combo, for: .toggleComposer)

        XCTAssertNil(model.recordingGlobalShortcutAction)
        XCTAssertEqual(model.preferences.globalShortcuts.toggleComposer, combo)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleComposer], .active)
        XCTAssertEqual(Set(registrar.active.keys), [combo])
        XCTAssertEqual(log.saves, 1)
    }

    func testRegistrationFailureKeepsPreviousShortcutWithoutSaving() {
        let previous = shortcut(kVK_ANSI_K, [.control, .option])
        let taken = shortcut(kVK_ANSI_M, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.globalShortcuts.toggleComposer = previous
        let registrar = FakeGlobalHotKeyRegistrar()
        registrar.unavailable = [taken]
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)
        controller.start()

        controller.beginRecording(.toggleComposer)
        controller.record(taken, for: .toggleComposer)

        XCTAssertNil(model.recordingGlobalShortcutAction)
        XCTAssertEqual(model.preferences.globalShortcuts.toggleComposer, previous)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleComposer], .rejected(.unavailable))
        XCTAssertEqual(Set(registrar.active.keys), [previous])
        XCTAssertEqual(log.saves, 0)
        XCTAssertEqual(GlobalShortcutRejection.unavailable.message, "다른 앱이 이미 사용 중이라 등록할 수 없어요.")
    }

    func testInvalidRecordingKeepsPreviousShortcutAndIsNeverRegistered() {
        let previous = shortcut(kVK_ANSI_K, [.control, .option])
        let overlay = shortcut(kVK_ANSI_O, [.control, .option])
        let singleModifier = shortcut(kVK_ANSI_M, [.command])
        let spotlight = shortcut(kVK_Space, [.command])
        var preferences = AppPreferences.defaults
        preferences.globalShortcuts.toggleComposer = previous
        preferences.globalShortcuts.toggleOverlay = overlay
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)
        controller.start()

        controller.beginRecording(.toggleComposer)
        controller.record(singleModifier, for: .toggleComposer)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleComposer], .rejected(.modifiersRequired))

        controller.beginRecording(.toggleComposer)
        controller.record(overlay, for: .toggleComposer)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleComposer], .rejected(.assigned(to: .toggleOverlay)))

        controller.beginRecording(.toggleComposer)
        controller.record(spotlight, for: .toggleComposer)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleComposer], .rejected(.reservedBySystem))

        XCTAssertEqual(model.preferences.globalShortcuts.toggleComposer, previous)
        XCTAssertEqual(model.globalShortcutStatuses[.toggleOverlay], .active)
        XCTAssertEqual(Set(registrar.active.keys), [previous, overlay])
        XCTAssertFalse(registrar.attempts.contains(singleModifier))
        XCTAssertFalse(registrar.attempts.contains(spotlight))
        XCTAssertEqual(log.saves, 0)
    }

    func testClearingUnregistersShortcutAndSavesOnce() {
        let quiet = shortcut(kVK_ANSI_Q, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.globalShortcuts.toggleQuietMode = quiet
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)
        controller.start()

        controller.clear(.toggleQuietMode)
        registrar.press(quiet)
        controller.clear(.toggleQuietMode)

        XCTAssertNil(model.preferences.globalShortcuts.toggleQuietMode)
        XCTAssertNil(model.globalShortcutStatuses[.toggleQuietMode])
        XCTAssertTrue(registrar.active.isEmpty)
        XCTAssertTrue(log.calls.isEmpty)
        XCTAssertEqual(log.saves, 1)
    }

    func testOverlayAndQuietModeShortcutsUseMenuActions() {
        let overlay = shortcut(kVK_ANSI_O, [.control, .option])
        let quiet = shortcut(kVK_ANSI_Q, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.globalShortcuts.toggleOverlay = overlay
        preferences.globalShortcuts.toggleQuietMode = quiet
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, _) = makeController(preferences: preferences, registrar: registrar, log: log)
        controller.start()

        registrar.press(overlay)
        registrar.press(quiet)

        XCTAssertEqual(log.calls, ["toggleOverlay", "toggleQuietMode"])
    }

    func testComposerShortcutClosesVisibleComposerAndOpensItOtherwise() {
        let composer = shortcut(kVK_ANSI_K, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.onboardingComplete = true
        preferences.globalShortcuts.toggleComposer = composer
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)
        model.rooms = [Self.room()]
        controller.start()
        log.composerVisible = true

        registrar.press(composer)

        XCTAssertEqual(log.calls, ["dismissComposer"])
        XCTAssertFalse(log.composerVisible)

        registrar.press(composer)

        XCTAssertEqual(log.calls, ["dismissComposer", "openComposer"])
        XCTAssertTrue(log.composerVisible)
    }

    func testComposerShortcutOpensMainWindowWhenComposerCannotAppear() {
        let composer = shortcut(kVK_ANSI_K, [.control, .option])
        var preferences = AppPreferences.defaults
        preferences.onboardingComplete = true
        preferences.globalShortcuts.toggleComposer = composer
        let registrar = FakeGlobalHotKeyRegistrar()
        let log = ShortcutCommandLog()
        let (controller, model) = makeController(preferences: preferences, registrar: registrar, log: log)
        model.rooms = [Self.room()]
        controller.start()

        // The menu path can silently ignore the request, for example while the overlay is still hidden.
        log.opensComposer = false
        registrar.press(composer)

        XCTAssertEqual(log.calls, ["openComposer", "openMainWindow"])

        log.calls.removeAll()
        model.rooms = []
        registrar.press(composer)

        XCTAssertEqual(log.calls, ["openMainWindow"])

        log.calls.removeAll()
        model.rooms = [Self.room()]
        model.preferences.onboardingComplete = false
        registrar.press(composer)

        XCTAssertEqual(log.calls, ["openMainWindow"])
    }

    private func shortcut<Code: BinaryInteger>(
        _ keyCode: Code,
        _ modifiers: GlobalShortcutModifiers
    ) -> GlobalShortcut {
        GlobalShortcut(keyCode: UInt32(keyCode), modifiers: modifiers)
    }

    private func rejection<Code: BinaryInteger>(
        _ keyCode: Code,
        _ modifiers: GlobalShortcutModifiers,
        for action: GlobalShortcutAction = .toggleComposer,
        among assignments: GlobalShortcutAssignments = GlobalShortcutAssignments()
    ) -> GlobalShortcutRejection? {
        shortcut(keyCode, modifiers).rejection(for: action, among: assignments)
    }

    private func encodedJSON(_ shortcut: GlobalShortcut) throws -> String {
        let data = try JSONEncoder().encode(shortcut)
        return String(decoding: data, as: UTF8.self)
    }

    private func makeController(
        preferences: AppPreferences = .defaults,
        registrar: FakeGlobalHotKeyRegistrar,
        log: ShortcutCommandLog
    ) -> (GlobalShortcutController, AppModel) {
        let model = AppModel(preferences: preferences)
        let controller = GlobalShortcutController(
            model: model,
            registrar: registrar,
            commands: log.commands(),
            onPreferencesChanged: { log.saves += 1 }
        )
        return (controller, model)
    }

    private static func room() -> Room {
        Room(
            id: UUID(),
            name: "단축키 그룹",
            ownerID: UUID(),
            members: [],
            inviteCodeHint: "••••-••AA"
        )
    }
}

@MainActor
private final class FakeGlobalHotKeyRegistrar: GlobalHotKeyRegistering {
    var unavailable: Set<GlobalShortcut> = []
    private(set) var active: [GlobalShortcut: GlobalHotKeyRegistration] = [:]
    private(set) var attempts: [GlobalShortcut] = []
    private var handlers: [GlobalHotKeyRegistration: () -> Void] = [:]
    private var nextIdentifier: UInt32 = 0

    func register(
        _ shortcut: GlobalShortcut,
        onPress: @escaping () -> Void
    ) -> Result<GlobalHotKeyRegistration, GlobalHotKeyRegistrationError> {
        attempts.append(shortcut)
        guard !unavailable.contains(shortcut), active[shortcut] == nil else {
            return .failure(GlobalHotKeyRegistrationError(status: OSStatus(eventHotKeyExistsErr)))
        }
        nextIdentifier += 1
        let registration = GlobalHotKeyRegistration(id: nextIdentifier)
        active[shortcut] = registration
        handlers[registration] = onPress
        return .success(registration)
    }

    func unregister(_ registration: GlobalHotKeyRegistration) {
        handlers[registration] = nil
        active = active.filter { $0.value != registration }
    }

    func press(_ shortcut: GlobalShortcut) {
        guard let registration = active[shortcut] else { return }
        handlers[registration]?()
    }
}

@MainActor
private final class ShortcutCommandLog {
    var calls: [String] = []
    var composerVisible = false
    var opensComposer = true
    var saves = 0

    func commands() -> GlobalShortcutCommands {
        GlobalShortcutCommands(
            isComposerVisible: { self.composerVisible },
            openComposer: {
                self.calls.append("openComposer")
                if self.opensComposer { self.composerVisible = true }
            },
            dismissComposer: {
                self.calls.append("dismissComposer")
                self.composerVisible = false
            },
            openMainWindow: { self.calls.append("openMainWindow") },
            toggleOverlay: { self.calls.append("toggleOverlay") },
            toggleQuietMode: { self.calls.append("toggleQuietMode") }
        )
    }
}
