import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';

/// Free on-device OCR: [image_picker] + [google_mlkit_text_recognition].
/// No paid OCR. Extracted text remains unverified until user review.
///
/// Inject [pickImage] / [recognizePath] to unit-test without native plugins.
class OcrService {
  OcrService({
    ImagePicker? picker,
    TextRecognizer? recognizer,
    Future<XFile?> Function({required ImageSource source})? pickImage,
    Future<String> Function(String path)? recognizePath,
  })  : _picker = picker ?? ImagePicker(),
        _recognizer = recognizer,
        _pickImage = pickImage,
        _recognizePath = recognizePath;

  final ImagePicker _picker;
  TextRecognizer? _recognizer;
  final Future<XFile?> Function({required ImageSource source})? _pickImage;
  final Future<String> Function(String path)? _recognizePath;
  bool _ownsRecognizer = false;

  TextRecognizer get _textRecognizer {
    if (_recognizer != null) return _recognizer!;
    _recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    _ownsRecognizer = true;
    return _recognizer!;
  }

  /// Pick from camera or gallery, then run on-device text recognition.
  /// Returns `null` if the user cancels the picker.
  Future<String?> pickAndRecognize({required ImageSource source}) async {
    final pick = _pickImage;
    final file = pick != null
        ? await pick(source: source)
        : await _picker.pickImage(
            source: source,
            imageQuality: 85,
            maxWidth: 2048,
          );
    if (file == null) return null;
    final text = await recognizeFromPath(file.path);
    return text;
  }

  /// Recognize text from a local image path (camera/gallery temp file).
  Future<String> recognizeFromPath(String path) async {
    final custom = _recognizePath;
    if (custom != null) {
      return (await custom(path)).trim();
    }
    final input = InputImage.fromFilePath(path);
    final recognized = await _textRecognizer.processImage(input);
    return recognized.text.trim();
  }

  Future<void> dispose() async {
    if (_ownsRecognizer && _recognizer != null) {
      await _recognizer!.close();
      _recognizer = null;
      _ownsRecognizer = false;
    }
  }
}
