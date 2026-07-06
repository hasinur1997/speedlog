# NST-903 — Code signing & notarization

- **Epic:** EPIC-09 Autostart & Packaging
- **Type:** Task
- **Priority:** P2
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-902

## Description
Sign and notarize the .app so it opens on other Macs without Gatekeeper "damaged" warnings.
Requires an Apple Developer ID (user action).

## Acceptance criteria
- [ ] `packaging/sign-and-notarize.sh`: codesign --deep --options runtime with
      Developer ID Application cert; hardened runtime entitlements file committed
- [ ] `xcrun notarytool submit --wait` + `xcrun stapler staple` scripted
- [ ] DMG (or zip) creation step for distribution
- [ ] `packaging/SIGNING.md`: prerequisites (Apple Developer account, cert creation,
      app-specific password / keychain profile), step-by-step run guide
- [ ] Verified: signed app opens cleanly on a second Mac (or documented as pending
      Developer ID availability — ticket may end BLOCKED on user credentials)

## Technical notes
PyInstaller bundles need every embedded dylib/binary signed — `--deep` usually works
but verify with `codesign --verify --deep --strict` and `spctl -a -vv`.

## Test plan
Script dry-run mode; manual verification checklist in SIGNING.md.

## Implementation notes (fill after DONE)
