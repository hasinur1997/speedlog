# NST-905 — Feature gate module (Free vs Pro)

- **Epic:** EPIC-09 Autostart & Packaging (Commercial)
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-802

## Description
Single thin gating layer for the Free/Pro split. v1 has NO license validation backend —
just a clean seam so payments (Paddle/Lemon Squeezy/App Store IAP) can plug in later
without touching feature code.

## Acceptance criteria
- [ ] `gate.py`: `is_pro() -> bool` — v1 reads `config.PRO_FEATURES_ENABLED`
      (default True in dev builds, False in release build flag)
- [ ] Exactly TWO call sites in v1 (checked at UI boundary only):
      1) PDF Export button — Free: enabled-looking button opens an upgrade dialog
         (title, one-line pitch from marketing-copy.md, "Learn more" URL placeholder)
      2) Retention purge condition (NST-904)
- [ ] No license checks scattered anywhere else (grep-verified)
- [ ] Upgrade dialog copy sourced from a constants module, not hardcoded strings

## Technical notes
Deliberately naive: real entitlement storage/receipt validation is a future ticket when
a payment provider is chosen. Do not build crypto/obfuscation now.

## Test plan
pytest-qt: is_pro False → export click shows upgrade dialog, no file dialog;
is_pro True → normal export flow (from NST-802 tests).

## Implementation notes (fill after DONE)
