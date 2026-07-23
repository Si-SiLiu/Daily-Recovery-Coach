import Cocoa
import WebKit

final class DashboardAppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!

    func applicationDidFinishLaunching(_ notification: Notification) {
        let frame = NSRect(x: 0, y: 0, width: 1280, height: 820)
        window = NSWindow(
            contentRect: frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Daily Recovery Coach"
        window.center()
        window.setFrameAutosaveName("DailyRecoveryCoachWindow")

        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        webView = WKWebView(frame: frame, configuration: configuration)
        webView.navigationDelegate = self
        window.contentView = webView
        showLoadingPage()

        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        startDashboard()
    }

    func applicationShouldTerminateAfterLastWindowClosed(
        _ sender: NSApplication
    ) -> Bool {
        return true
    }

    private func showLoadingPage() {
        let html = """
        <!doctype html>
        <html lang="zh-CN">
        <meta charset="utf-8">
        <style>
          body { font-family: -apple-system; display: grid; place-items: center;
                 height: 100vh; margin: 0; background: #f6f8fb; color: #243447; }
          main { text-align: center; }
          .dot { display: inline-block; animation: pulse 1.2s infinite; }
          @keyframes pulse { 50% { opacity: .25; } }
        </style>
        <main><h2>Daily Recovery Coach</h2>
        <p class="dot">正在启动本地数据看板…</p></main>
        </html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }

    private func startDashboard() {
        DispatchQueue.global(qos: .userInitiated).async {
            let projectRoot = "/Users/liuxi/Documents/Daily·Recovery·Coach"
            let process = Process()
            let output = Pipe()
            process.executableURL = URL(
                fileURLWithPath: projectRoot + "/.venv/bin/python"
            )
            process.arguments = [
                projectRoot + "/src/dashboard_launcher.py",
                "--no-browser"
            ]
            process.currentDirectoryURL = URL(fileURLWithPath: projectRoot)
            process.standardOutput = output
            process.standardError = output

            do {
                try process.run()
                process.waitUntilExit()
                let data = output.fileHandleForReading.readDataToEndOfFile()
                let message = String(data: data, encoding: .utf8) ?? ""
                guard process.terminationStatus == 0,
                      let url = self.dashboardURL(from: message) else {
                    self.showLaunchError(message: message)
                    return
                }
                DispatchQueue.main.async {
                    self.webView.load(URLRequest(url: url))
                }
            } catch {
                self.showLaunchError(message: "DASHBOARD_APP_LAUNCH_FAILED")
            }
        }
    }

    private func dashboardURL(from output: String) -> URL? {
        for line in output.split(separator: "\n") {
            let prefix = "Dashboard: "
            if line.hasPrefix(prefix) {
                let value = String(line.dropFirst(prefix.count))
                guard value.hasPrefix("http://127.0.0.1:") else { return nil }
                return URL(string: value)
            }
        }
        return nil
    }

    private func showLaunchError(message: String) {
        let safeMessage = message
            .split(separator: "\n")
            .last
            .map(String.init) ?? "DASHBOARD_APP_LAUNCH_FAILED"
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.alertStyle = .critical
            alert.messageText = "无法启动本地数据看板"
            alert.informativeText = safeMessage
            alert.addButton(withTitle: "关闭")
            alert.runModal()
            NSApp.terminate(nil)
        }
    }
}

let application = NSApplication.shared
let delegate = DashboardAppDelegate()
application.setActivationPolicy(.regular)
application.delegate = delegate
application.run()
