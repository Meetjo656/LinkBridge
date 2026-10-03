import UIKit

/**
 * LinkBridge iOS Custom Keyboard Extension (UIInputViewController)
 *
 * Designed around textDocumentProxy's limited context:
 * - Monitors text immediately preceding the insertion point (documentContextBeforeInput).
 * - When an App Store link is detected, the 🔗 toolbar button activates.
 * - Tapping 🔗 sends a single network request to POST /universalize.
 * - Safely replaces the detected URL with the returned LinkBridge universal short link.
 *
 * State flow:
 * [🔗 (idle/disabled)] -> App Store link detected -> [🔗 (active)]
 *   -> Tap -> [⏳ (loading/prevent multi-tap)]
 *   -> Response received -> Insert short URL -> [✓ (success)]
 *   -> [🔗 (disabled until next link)]
 */
class LinkBridgeKeyboardViewController: UIInputViewController {

    // =========================================================================
    // API BASE URL CONFIGURATION
    // -------------------------------------------------------------------------
    // 1. iOS Simulator (running on macOS with backend on localhost):
    //    "http://127.0.0.1:8000"
    //
    // 2. Physical iPhone / Device Testing over local Wi-Fi:
    //    "http://192.168.1.XX:8000" (replace XX with your computer's LAN IP)
    //    Note: On a real iPhone, 127.0.0.1 refers to the iPhone itself. To reach
    //    your development machine, specify your computer's local Wi-Fi IP.
    //
    // 3. Production Deployment (Public HTTPS):
    //    "https://api.linkbridge.app"
    // =========================================================================
    private let apiBaseUrl = "http://192.168.1.XX:8000" // Configure for your testing environment

    // UI Components
    private var toolbarView: UIStackView!
    private var linkButton: UIButton!

    // State Tracking
    private var detectedUrl: String?
    private var isLoading = false

    // App Store URL detection pattern
    private let appStoreRegex = try! NSRegularExpression(
        pattern: "https?://(?:[a-zA-Z0-9-]+\\.)?(?:apps|itunes)\\.apple\\.com/[^\\s]+",
        options: .caseInsensitive
    )

    override func viewDidLoad() {
        super.viewDidLoad()
        setupToolbar()
    }

    override func textDidChange(_ textInput: UITextInput?) {
        super.textDidChange(textInput)
        inspectContext()
    }

    // MARK: - UI Setup

    private func setupToolbar() {
        toolbarView = UIStackView()
        toolbarView.axis = .horizontal
        toolbarView.distribution = .fillEqually
        toolbarView.spacing = 8
        toolbarView.translatesAutoresizingMaskIntoConstraints = false

        let translateBtn = createToolbarButton(title: "Translate")
        let gifBtn = createToolbarButton(title: "GIF")
        let clipboardBtn = createToolbarButton(title: "Clipboard")

        linkButton = UIButton(type: .system)
        linkButton.titleLabel?.font = UIFont.systemFont(ofSize: 20)
        linkButton.layer.cornerRadius = 8
        linkButton.addTarget(self, action: #selector(didTapLinkButton), for: .touchUpInside)

        setButtonState(.disabled)

        toolbarView.addArrangedSubview(translateBtn)
        toolbarView.addArrangedSubview(gifBtn)
        toolbarView.addArrangedSubview(clipboardBtn)
        toolbarView.addArrangedSubview(linkButton)

        view.addSubview(toolbarView)

        NSLayoutConstraint.activate([
            toolbarView.topAnchor.constraint(equalTo: view.topAnchor, constant: 4),
            toolbarView.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 8),
            toolbarView.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -8),
            toolbarView.heightAnchor.constraint(equalToConstant: 44)
        ])
    }

    private func createToolbarButton(title: String) -> UIButton {
        let btn = UIButton(type: .system)
        btn.setTitle(title, for: .normal)
        btn.titleLabel?.font = UIFont.systemFont(ofSize: 13, weight: .medium)
        btn.setTitleColor(.secondaryLabel, for: .normal)
        return btn
    }

    // MARK: - Button State Machine

    private enum ButtonVisualState {
        case disabled
        case active
        case loading
        case success
    }

    private func setButtonState(_ state: ButtonVisualState) {
        switch state {
        case .disabled:
            isLoading = false
            linkButton.setTitle("🔗", for: .normal)
            linkButton.isEnabled = false
            linkButton.alpha = 0.4
            linkButton.backgroundColor = UIColor.systemGray5
        case .active:
            isLoading = false
            linkButton.setTitle("🔗", for: .normal)
            linkButton.isEnabled = true
            UIView.animate(withDuration: 0.2) {
                self.linkButton.alpha = 1.0
                self.linkButton.backgroundColor = UIColor.systemBlue
            }
        case .loading:
            isLoading = true
            linkButton.setTitle("⏳", for: .normal)
            linkButton.isEnabled = false
            linkButton.alpha = 0.8
            linkButton.backgroundColor = UIColor.systemBlue.withAlphaComponent(0.6)
        case .success:
            isLoading = false
            linkButton.setTitle("✓", for: .normal)
            linkButton.isEnabled = false
            UIView.animate(withDuration: 0.2) {
                self.linkButton.alpha = 1.0
                self.linkButton.backgroundColor = UIColor.systemGreen
            }
        }
    }

    // MARK: - Core Keyboard Logic

    @objc private func didTapLinkButton() {
        guard let url = detectedUrl, !isLoading else { return }
        resolve(url: url)
    }

    /// 1. Inspect text immediately before cursor in documentContextBeforeInput.
    private func inspectContext() {
        // Prevent changing button state while network request is in flight
        guard !isLoading else { return }

        guard let text = textDocumentProxy.documentContextBeforeInput, !text.isEmpty else {
            detectedUrl = nil
            setButtonState(.disabled)
            return
        }

        let range = NSRange(location: 0, length: text.utf16.count)
        let matches = appStoreRegex.matches(in: text, options: [], range: range)

        // Find match immediately preceding or closest to the cursor
        if let lastMatch = matches.last, let matchRange = Range(lastMatch.range, in: text) {
            let url = String(text[matchRange])
            detectedUrl = url
            setButtonState(.active)
        } else {
            detectedUrl = nil
            setButtonState(.disabled)
        }
    }

    /// 2. Call POST /universalize in a single network request.
    private func resolve(url: String) {
        setButtonState(.loading)

        guard let endpoint = URL(string: "\(apiBaseUrl)/universalize") else {
            setButtonState(.disabled)
            return
        }

        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 8.0

        let body = ["url": url]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }

            guard
                let data = data,
                error == nil,
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                let status = json["status"] as? String,
                status == "matched",
                let shortURL = json["short_url"] as? String
            else {
                DispatchQueue.main.async {
                    // Revert to active if URL still present, else disabled
                    self.inspectContext()
                }
                return
            }

            DispatchQueue.main.async {
                self.setButtonState(.success)
                self.insert(shortURL: shortURL)

                // Brief success feedback before returning to idle
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { [weak self] in
                    self?.detectedUrl = nil
                    self?.setButtonState(.disabled)
                }
            }
        }.resume()
    }

    /// 3. Safely replace original link text before cursor with short universal link.
    private func insert(shortURL: String) {
        guard let originalUrl = detectedUrl else {
            textDocumentProxy.insertText(shortURL)
            return
        }

        let proxy = textDocumentProxy

        // Delete text input units corresponding to the original URL
        if let context = proxy.documentContextBeforeInput {
            if context.hasSuffix(originalUrl) {
                // Original URL is right at the cursor
                for _ in 0..<originalUrl.utf16.count {
                    proxy.deleteBackward()
                }
            } else if let matchRange = context.range(of: originalUrl, options: .backwards) {
                // If trailing whitespace or characters were entered after the URL
                let trailingChars = context[matchRange.upperBound...]
                let totalUnitsToDelete = originalUrl.utf16.count + trailingChars.utf16.count
                for _ in 0..<totalUnitsToDelete {
                    proxy.deleteBackward()
                }
            }
        }

        proxy.insertText(shortURL)
    }
}
