# NST-902 — PyInstaller macOS .app packaging

- **Epic:** EPIC-09 Autostart & Packaging
- **Type:** Task
- **Priority:** P1
- **Estimate:** L
- **Status:** TODO
- **Depends on:** All Milestone 1–4 tickets DONE

## Description
Produce a distributable `Speedlog.app`.

## Acceptance criteria
- [ ] `packaging/speedlog.spec` committed; `make app` (or build script) produces
      the .app in one command
- [ ] Bundle: windowed (no console), icon (.icns), Info.plist with LSUIElement=true
      (menu-bar app: no Dock icon), CFBundleIdentifier=com.speedlog.app,
      version from single VERSION source
- [ ] App launches on a clean macOS user account: tray appears, tracking works,
      DB + logs created under ~/Library
- [ ] PDF export works from the bundle (reportlab data files included via spec)
- [ ] Documented known-good PyInstaller + PySide6 versions in the spec header

## Technical notes
Watch: PySide6 plugin collection, psutil C-extension, reportlab fonts. Test on both
Apple Silicon and Intel if possible (or note arch of build).

## Test plan
Manual smoke checklist committed as `packaging/SMOKE-TEST.md` and executed.

## Implementation notes (fill after DONE)
