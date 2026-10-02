/**
 * LinkBridge Keyboard Controller Module
 * Handles smart link detection, toolbar button activation, and universal link insertion.
 */

const APP_LINK_REGEX = /(https?:\/\/(?:[a-zA-Z0-9-]+\.)?(?:apps|itunes)\.apple\.com\/[^\s]+|https?:\/\/play\.google\.com\/store\/apps\/details\?[^\s]+)/i;

export class LinkBridgeKeyboard {
  constructor(options = {}) {
    this.apiBaseUrl = options.apiBaseUrl || 'http://127.0.0.1:8000';
    this.onStateChange = options.onStateChange || (() => {});
    this.currentDetectedUrl = null;
  }

  /**
   * Check if current text contains an App Store or Play Store link.
   * If detected, activates the 🔗 button; otherwise disables it.
   */
  inspectText(text) {
    if (!text) {
      this.currentDetectedUrl = null;
      this.onStateChange({ hasLink: false, url: null });
      return null;
    }

    const match = text.match(APP_LINK_REGEX);
    this.currentDetectedUrl = match ? match[0] : null;

    this.onStateChange({
      hasLink: Boolean(this.currentDetectedUrl),
      url: this.currentDetectedUrl,
    });

    return this.currentDetectedUrl;
  }

  /**
   * Executed when the user taps 🔗.
   * Resolves the app equivalent, creates a short link, and replaces the URL in the text.
   */
  async convertLink(currentText) {
    const originalUrl = this.inspectText(currentText);
    if (!originalUrl) {
      throw new Error('No supported app store link found in text');
    }

    // 1. POST /resolve
    const resolveRes = await fetch(`${this.apiBaseUrl}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ long_url: originalUrl }),
    });
    const resolveData = await resolveRes.json();

    if (resolveData.status !== 'matched') {
      return {
        success: false,
        reason: resolveData.reason || 'unsupported',
        text: currentText,
      };
    }

    // 2. POST /links
    const linkRes = await fetch(`${this.apiBaseUrl}/links`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ios_url: resolveData.ios_url,
        android_url: resolveData.android_url,
      }),
    });
    const linkData = await linkRes.json();

    // 3. Replace original link with Universal LinkBridge URL
    const updatedText = currentText.replace(originalUrl, linkData.short_url);

    return {
      success: true,
      short_url: linkData.short_url,
      short_code: linkData.short_code,
      updated_text: updatedText,
      app_name: resolveData.app_name,
    };
  }
}
