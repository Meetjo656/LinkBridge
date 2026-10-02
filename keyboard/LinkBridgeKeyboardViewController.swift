import UIKit

/**
 * LinkBridge iOS Custom Keyboard Extension (UIInputViewController)
 *
 * Implements the smart LinkBridge toolbar:
 * [ Translate | GIF | Clipboard | 🔗 ]
 *
 * Dumb keyboard, deterministic backend:
 * 1. Automatically inspects document text before/around cursor.
 * 2. If an App Store link (apps.apple.com) is detected, the 🔗 button lights up.
 * 3. User taps 🔗 -> Calls /resolve and /links -> Inserts LinkBridge universal link.
 */
class LinkBridgeKeyboardViewController: UIInputViewController {

    private let apiBaseUrl = "http://127.0.0.1:8000" // or production https://linkbridge.app

    private var toolbarView: UIStackView!
    private var linkButton: UIButton!
    private var detectedUrl: String?

    private let appStoreRegex = try! NSRegularExpression(
        pattern: "https?://(?:[a-zA-Z0-9-]+\\.)?apps\\.apple\\.com/[^\\s]+",
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
        linkButton.setTitle("🔗", for: .normal)
        linkButton.titleLabel?.font = UIFont.systemFont(ofSize: 20)
        linkButton.backgroundColor = UIColor.systemGray5
        linkButton.layer.cornerRadius = 8
        linkButton.isEnabled = false
        linkButton.alpha = 0.4
        linkButton.addTarget(self, action: #selector(didTapLinkButton), for: .touchUpInside)

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

    private func inspectContext() {
        guard let proxy = textDocumentProxy as? UITextDocumentProxy,
              let text = proxy.documentContextBeforeInput else {
            setLinkButtonActive(false, url: nil)
            return
        }

        let range = NSRange(location: 0, length: text.utf16.count)
        if let match = appStoreRegex.firstMatch(in: text, options: [], range: range),
           let matchRange = Range(match.range, in: text) {
            let url = String(text[matchRange])
            setLinkButtonActive(true, url: url)
        } else {
            setLinkButtonActive(false, url: nil)
        }
    }

    private func setLinkButtonActive(_ active: Bool, url: String?) {
        detectedUrl = url
        linkButton.isEnabled = active
        UIView.animate(withDuration: 0.2) {
            self.linkButton.alpha = active ? 1.0 : 0.4
            self.linkButton.backgroundColor = active ? UIColor.systemBlue : UIColor.systemGray5
        }
    }

    @objc private func didTapLinkButton() {
        guard let originalUrl = detectedUrl else { return }

        // 1. Call POST /resolve
        resolveAndInsert(originalUrl: originalUrl)
    }

    private func resolveAndInsert(originalUrl: String) {
        guard let resolveEndpoint = URL(string: "\(apiBaseUrl)/resolve") else { return }

        var request = URLRequest(url: resolveEndpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload = ["long_url": originalUrl]
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)

        URLSession.shared.dataTask(with: request) { [weak self] data, _, _ in
            guard let self = self,
                  let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let status = json["status"] as? String, status == "matched",
                  let iosUrl = json["ios_url"] as? String,
                  let androidUrl = json["android_url"] as? String else {
                return
            }

            // 2. Call POST /links
            self.createShortLink(originalUrl: originalUrl, iosUrl: iosUrl, androidUrl: androidUrl)
        }.resume()
    }

    private func createShortLink(originalUrl: String, iosUrl: String, androidUrl: String) {
        guard let linksEndpoint = URL(string: "\(apiBaseUrl)/links") else { return }

        var request = URLRequest(url: linksEndpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload = ["ios_url": iosUrl, "android_url": androidUrl]
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)

        URLSession.shared.dataTask(with: request) { [weak self] data, _, _ in
            guard let self = self,
                  let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let shortUrl = json["short_url"] as? String else {
                return
            }

            DispatchQueue.main.async {
                self.replaceUrlInDocument(originalUrl: originalUrl, with: shortUrl)
            }
        }.resume()
    }

    private func replaceUrlInDocument(originalUrl: String, with shortUrl: String) {
        let proxy = textDocumentProxy

        // Delete previous characters matching originalUrl length and insert universal link
        for _ in 0..<originalUrl.count {
            proxy.deleteBackward()
        }
        proxy.insertText(shortUrl)
        self.setLinkButtonActive(false, url: nil)
    }
}
