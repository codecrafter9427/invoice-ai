import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:invoice_ai/services/ocr_service.dart';

void main() {
  group('OcrService (fakes)', () {
    test('pickAndRecognize returns recognized text from camera', () async {
      ImageSource? seenSource;
      final service = OcrService(
        pickImage: ({required ImageSource source}) async {
          seenSource = source;
          return XFile('fake/invoice.jpg');
        },
        recognizePath: (path) async {
          expect(path, 'fake/invoice.jpg');
          return '  Invoice Number: INV-OCR-01\nTotal: \$10.00  ';
        },
      );

      final text = await service.pickAndRecognize(source: ImageSource.camera);

      expect(seenSource, ImageSource.camera);
      expect(text, 'Invoice Number: INV-OCR-01\nTotal: \$10.00');
      await service.dispose();
    });

    test('pickAndRecognize returns null when user cancels', () async {
      final service = OcrService(
        pickImage: ({required ImageSource source}) async => null,
        recognizePath: (_) async => 'should not run',
      );

      final text = await service.pickAndRecognize(source: ImageSource.gallery);

      expect(text, isNull);
      await service.dispose();
    });

    test('pickAndRecognize uses gallery source', () async {
      ImageSource? seenSource;
      final service = OcrService(
        pickImage: ({required ImageSource source}) async {
          seenSource = source;
          return XFile('fake/gallery.png');
        },
        recognizePath: (_) async => 'gallery text',
      );

      final text = await service.pickAndRecognize(source: ImageSource.gallery);

      expect(seenSource, ImageSource.gallery);
      expect(text, 'gallery text');
      await service.dispose();
    });

    test('recognizeFromPath trims whitespace', () async {
      final service = OcrService(
        recognizePath: (_) async => '\n  hello OCR  \n',
      );

      expect(await service.recognizeFromPath('any.jpg'), 'hello OCR');
      await service.dispose();
    });

    test('empty recognition result is empty string', () async {
      final service = OcrService(
        pickImage: ({required ImageSource source}) async =>
            XFile('blank.jpg'),
        recognizePath: (_) async => '   ',
      );

      final text = await service.pickAndRecognize(source: ImageSource.camera);

      expect(text, '');
      await service.dispose();
    });
  });
}
