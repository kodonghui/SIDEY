import Foundation
#if !APP_STORE
import Sparkle
#endif

@MainActor
protocol AppUpdateChecking: AnyObject {
    var canCheckForUpdates: Bool { get }
    func checkForUpdates()
}

@MainActor
final class NoUpdateController: AppUpdateChecking {
    var canCheckForUpdates: Bool { false }
    func checkForUpdates() {}
}

#if !APP_STORE
@MainActor
final class SparkleUpdateController: AppUpdateChecking {
    private let controller: SPUStandardUpdaterController?

    init(
        releaseChannel: AppReleaseChannel = .resolve(),
        startingUpdater: Bool = true
    ) {
#if CORTHEX_CUSTOM_BUILD
        // Personal builds must not replace themselves with the official release.
        controller = nil
#else
        if releaseChannel == .production {
            controller = SPUStandardUpdaterController(
                startingUpdater: startingUpdater,
                updaterDelegate: nil,
                userDriverDelegate: nil
            )
        } else {
            controller = nil
        }
#endif
    }

    var canCheckForUpdates: Bool {
        controller?.updater.canCheckForUpdates ?? false
    }

    func checkForUpdates() {
        controller?.checkForUpdates(nil)
    }
}
#endif
