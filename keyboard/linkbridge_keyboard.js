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
   * Universalizes the app store link in a single network round-trip.
   */
  async convertLink(currentText) {
    const originalUrl = this.inspectText(currentText);
    if (!originalUrl) {
      throw new Error('No supported app store link found in text');
    }

    // Single request to POST /universalize
    const res = await fetch(`${this.apiBaseUrl}/universalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: originalUrl }),
    });
    const data = await res.json();

    if (data.status !== 'matched') {
      return {
        success: false,
        reason: data.reason || 'unsupported',
        text: currentText,
      };
    }

    // Replace original link with Universal LinkBridge URL
    const updatedText = currentText.replace(originalUrl, data.short_url);

    return {
      success: true,
      short_url: data.short_url,
      short_code: data.short_code,
      updated_text: updatedText,
      app_name: data.app_name,
    };
  }
}
