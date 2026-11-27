# Invoice AI — Flutter mobile

Real Flutter app (not a WebView) for demo login, invoice list, and capture draft against the shared FastAPI backend.

**M5:** Camera/gallery → free on-device ML Kit OCR → review → save draft (`submit_for_review: false`). Paste-text fallback kept. No paid OCR, no offline queue, no auto-approve.

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
| Capture | Camera/gallery (ML Kit) **or** paste → `POST /api/v1/ai/invoice-extract` → review checkbox → `POST /api/v1/invoices` with `submit_for_review: false` |

## OCR policy (M5)

- **No paid OCR.** On-device only: `image_picker` + `google_mlkit_text_recognition`.
- Flow: pick image → ML Kit text → editable field → extract assist → **required review checkbox** → draft save.
- Backend extract still returns `ocr_verified=false` until the user reviews; messaging surfaces that explicitly.
- Paste fallback remains for demos without a camera.
- Draft create never sets `submit_for_review: true` and never auto-approves.

## Permissions

| Platform | Declared |
|----------|----------|
| Android | `CAMERA`, `READ_MEDIA_IMAGES`, legacy `READ_EXTERNAL_STORAGE` (≤32), `INTERNET`; camera feature optional |
| iOS | `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription` (+ add / mic plugin strings) |

## Offline drafts

Local offline draft queue is **out of scope** for M5. Capture requires API reachability for extract + create.

## Tests

```bash
cd products/invoice-ai/mobile
flutter test
```

- `test/ocr_service_test.dart` — unit tests with injected fakes (no native ML Kit)
- `test/widget_test.dart` — login smoke + Capture Camera/Gallery + review gate

## Known limitations

- Approvals / payments UI remain web-primary for the demo checklist.
- Duplicate warning surfaces after create via list flags.
- Prototype JWT auth only.
- ML Kit requires a real device/emulator for live OCR; unit tests use fakes.
