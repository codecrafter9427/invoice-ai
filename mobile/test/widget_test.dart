import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:invoice_ai/main.dart';
import 'package:invoice_ai/screens/capture_screen.dart';
import 'package:invoice_ai/screens/login_screen.dart';
import 'package:invoice_ai/services/ocr_service.dart';
import 'package:invoice_ai/services/session.dart';

void main() {
  setUp(() {
    Session.instance.clear();
  });

  testWidgets('LoginScreen shows Invoice AI branding and demo fields',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: LoginScreen()),
    );

    expect(find.text('Invoice AI'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('staff@invoiceai.local'), findsOneWidget);
  });

  testWidgets('InvoiceAiApp starts on login when logged out', (tester) async {
    await tester.pumpWidget(const InvoiceAiApp());
    await tester.pump();

    expect(find.text('Invoice AI'), findsWidgets);
    expect(find.text('Sign in'), findsOneWidget);
  });

  testWidgets('CaptureScreen enables Camera and Gallery; gates save on review',
      (tester) async {
    ImageSource? lastSource;
    final fakeOcr = OcrService(
      pickImage: ({required ImageSource source}) async {
        lastSource = source;
        return XFile('test.jpg');
      },
      recognizePath: (_) async =>
          'Invoice Number: INV-FAKE-99\nTotal: \$12.00',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: CaptureScreen(ocrService: fakeOcr),
      ),
    );
    // Allow supplier load Future to settle (will fail network; ignore).
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Run extract'), findsOneWidget);
    expect(find.text('Save capture draft'), findsOneWidget);

    await tester.tap(find.text('Camera'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(lastSource, ImageSource.camera);
    expect(
      find.textContaining('ocr_verified=false'),
      findsWidgets,
    );

    // Save without review checkbox → error.
    await tester.ensureVisible(find.text('Save capture draft'));
    await tester.tap(find.text('Save capture draft'));
    await tester.pump();

    expect(
      find.text('Confirm you reviewed extracted fields first.'),
      findsOneWidget,
    );

    // Check review → still needs supplier (none loaded without API).
    final checkbox = find.byType(CheckboxListTile);
    await tester.ensureVisible(checkbox);
    await tester.tap(checkbox);
    await tester.pump();
    await tester.tap(find.text('Save capture draft'));
    await tester.pump();

    expect(find.text('Select a supplier.'), findsOneWidget);
  });
}
