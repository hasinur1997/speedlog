# NST-406 — macOS app-menu name + real tray icon with always-visible live speed

- **Epic:** EPIC-04 app-shell-tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-402, NST-403

## Description
Three user-reported polish issues with the menu-bar presence:
1. The macOS application menu (top-left, next to the Apple menu) shows **"Python"**
   instead of **Speedlog**, because the process runs from the venv's Python.app bundle
   until NST-902 packages a real .app.
2. The tray (top-right menu bar) icon is a placeholder letter **"S"**; it should be a
   proper glyph that matches the monochrome template style of macOS menu-bar icons.
3. Live speed is only visible on hover (tooltip). It should be **always visible** in the
   menu bar while the app runs, e.g. `↓ 5.02 MB/s  ↑ 1.20 MB/s` (ui-context already
   describes "Icon + compact text if space allows").

## Acceptance criteria
- [x] On macOS, the app menu title reads "Speedlog", set without adding any new
      third-party dependency (ctypes + libobjc/CoreFoundation), applied before
      QApplication is created; a no-op that returns False on other platforms or when
      the bundle info dictionary is immutable.
- [x] Tray icon is a drawn speed-gauge glyph (template mask, light/dark adaptive) — no
      letter glyph.
- [x] While online, the menu bar shows the glyph plus live `↓ x  ↑ y` text rendered into
      the tray icon pixmap, updated at the existing 1/s throttle; tooltip keeps the same
      text.
- [x] While offline (and at startup), the menu bar shows the glyph plus `— offline`.
- [x] All pixmap sizes/fonts come from config constants; retina-crisp
      (devicePixelRatio-aware) rendering.

## Technical notes
- Unbundled Python: menu title comes from the main bundle's `CFBundleName`; patch the
  in-memory `NSBundle.mainBundle` info dictionary via `objc_msgSend` (verified mutable on
  macOS 15 / CPython 3.x). Guard with `respondsToSelector:setObject:forKey:`.
- QSystemTrayIcon has no text API on macOS; render text into a wide template QPixmap and
  `setIcon` — macOS sizes the status item to the image width.
- Keep `icon.setIsMask(True)` so the system recolors for light/dark menu bars.

## Test plan
- `tests/test_macos.py`: darwin-only test that `set_app_menu_name` returns True and the
  bundle name reads back; non-darwin path returns False (monkeypatched platform).
- `tests/test_tray.py`: icon with status text is wider than the bare glyph; icon changes
  (cacheKey) on `speed_sampled` and on offline `session_changed`; mask flag preserved;
  existing tooltip tests unchanged.

## Implementation notes (fill after DONE)
- New `app/macos.py`: `_ObjCRuntime` ctypes bridge (per-signature `objc_msgSend`
  prototypes — required on arm64) + `set_app_menu_name()` / `current_app_menu_name()`.
  Guarded by `respondsToSelector:` so an immutable info dictionary degrades to False
  instead of crashing. Called in `main()` before `QApplication(sys.argv)`.
- `app/ui/tray.py`: `tray_icon(status_text=None)` now paints a speedometer glyph
  (open arc + needle) and optionally the live speed text into one wide template pixmap
  at 2x devicePixelRatio; `on_speed_sampled` / `on_session_changed` update the icon and
  tooltip together under the existing 1/s throttle. Startup icon shows `— offline`.
- New config constants: `TRAY_PIXMAP_HEIGHT`, `TRAY_PIXMAP_SCALE`,
  `TRAY_TEXT_PIXEL_SIZE`, `TRAY_GLYPH_TEXT_GAP`. `APP_ICON_GLYPH` is still used by the
  window/dock icon in `main_window.app_icon()`.
- Tests: `tests/test_macos.py` (darwin round-trip + non-darwin no-op),
  `tests/test_tray.py` (mask flags, width growth with text, icon refresh on sample and
  on offline). The real menu-bar title/text was verified by launching the app locally.
- NST-902 (PyInstaller .app) should set CFBundleName properly; `set_app_menu_name`
  stays harmless then (it just rewrites the same value).
- Follow-up fix (user feedback, twice): text rendered into the status-item image ends
  up unreadably small on macOS (the image is scaled down to the menu bar), so that
  approach was dropped. Final design: the menu bar shows only the gauge template icon,
  and the live speed is a disabled status row at the top of the tray menu
  (`speed_action`, objectName `traySpeedAction`), updated with the tooltip under the
  same 1/s throttle; `— offline` when disconnected. `TRAY_TEXT_PIXEL_SIZE` /
  `TRAY_GLYPH_TEXT_GAP` constants were removed again with the text rendering.
