"""Playwright implementation for BrowserTool; install with `pip install .[browser]`."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright


class PlaywrightBrowserBackend:
    """Persistent Chromium session with explicit state inspection and artifact paths."""
    def __init__(self, profile_dir: str | Path = "data/browser-profile", headless: bool = True) -> None:
        self.profile_dir = Path(profile_dir); self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self.context: BrowserContext = self._playwright.chromium.launch_persistent_context(str(self.profile_dir), headless=headless, accept_downloads=True)
        self.page: Page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.on("dialog", lambda dialog: dialog.dismiss())

    def close(self) -> None:
        self.context.close(); self._playwright.stop()
    def navigate(self, url: str) -> None: self.page.goto(url, wait_until="domcontentloaded")
    def click(self, selector: str) -> None: self.page.locator(selector).click()
    def fill(self, selector: str, value: str) -> None: self.page.locator(selector).fill(value)
    def type(self, selector: str, value: str) -> None: self.page.locator(selector).press_sequentially(value)
    def press(self, key: str) -> None: self.page.keyboard.press(key)
    def wait_for(self, selector: str) -> None: self.page.locator(selector).wait_for()
    def upload(self, selector: str, path: str) -> None: self.page.locator(selector).set_input_files(path)
    def new_tab(self, url: str | None = None) -> None:
        self.page = self.context.new_page()
        if url: self.navigate(url)
    def select_tab(self, index: int) -> None: self.page = self.context.pages[index]
    def cookies(self) -> list[dict]: return self.context.cookies()
    def save_auth(self, path: str) -> None: self.context.storage_state(path=path)
    def content(self) -> str: return self.page.content()
    def url(self) -> str: return self.page.url
    def screenshot(self, path: str) -> None: self.page.screenshot(path=path, full_page=True)
