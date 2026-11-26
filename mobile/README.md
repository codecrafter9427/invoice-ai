# Invoice AI — Flutter mobile

Real Flutter app (not a WebView) for demo login, invoice list, and capture draft against the shared FastAPI backend.

## Flutter SDK (device run)

1. Install [Flutter](https://docs.flutter.dev/get-started/install) **3.22+** (stable) and ensure `flutter doctor` is clean for your target (Android SDK and/or Xcode).
2. Accept Android licenses: `flutter doctor --android-licenses`.
3. Start an emulator **or** connect a physical device with USB debugging.
4. From this folder:

```bash
cd products/invoice-ai/mobile
flutter pub get
flutter devices
flutter run
```

### API base URL

| Runtime | Typical base URL |
|---------|------------------|
| Android emulator | `http://10.0.2.2:8004` (default in app) |
| iOS simulator / desktop | `http://localhost:8004` |
| Physical device | `http://<your-LAN-IP>:8004` (enter on login) |

Backend must be running (`uvicorn app.main:app --reload --port 8004`) with seed data loaded.

Demo password for all seed users: **`demo`** (e.g. `staff@invoiceai.local`).

## Screens

| Screen | Behavior |
|--------|----------|
| Login | `POST /api/v1/auth/demo-login` |
| Home | Shortcuts + session role |
| Invoice list | `GET /api/v1/invoices` with search/status |
| Capture | Paste OCR/demo text → `POST /api/v1/ai/invoice-extract` → edit fields → `POST /api/v1/invoices` draft |

## OCR policy

- **No paid OCR.** Capture uses pasted text + DemoAIProvider extract (same as web).
- Optional free path (not wired by default): `image_picker` + `google_mlkit_text_recognition` for camera/gallery on-device text, then the same extract/create flow. Camera button is disabled until those packages are added.

## Offline drafts

Local offline draft queue is **Coming Soon** (M4 gap). Capture requires API reachability for create.

## Known limitations

- Approvals / payments UI remain web-primary for the demo checklist.
- Duplicate warning surfaces after create via list flags.
- Prototype JWT auth only.
