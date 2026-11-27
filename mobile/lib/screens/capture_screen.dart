import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api/client.dart';
import '../services/ocr_service.dart';
import '../services/session.dart';

/// Capture draft: camera/gallery OCR or paste → extract → review → save draft.
/// Uses free ML Kit only. Never auto-approves; `submit_for_review` stays false.
class CaptureScreen extends StatefulWidget {
  const CaptureScreen({
    super.key,
    this.ocrService,
  });

  /// Optional inject for tests; production creates a default [OcrService].
  final OcrService? ocrService;

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  static const _sample = '''Supplier: Northwind Office Supply
Invoice Number: INV-MOBILE-01
Invoice Date: 2026-11-20
Due Date: 2026-12-20
PO: PO-2026-0101
Paper ream case x 4 @ \$24.50 tax 8%
Subtotal: \$98.00
Tax: \$7.84
Total: \$105.84
Currency: USD
''';

  late final OcrService _ocrService;
  final _ocr = TextEditingController(text: _sample);
  final _invoiceNumber = TextEditingController();
  final _invoiceDate = TextEditingController(text: '2026-11-20');
  final _dueDate = TextEditingController(text: '2026-12-20');
  final _description = TextEditingController(text: 'Paper ream case');
  final _qty = TextEditingController(text: '4');
  final _unit = TextEditingController(text: '24.50');
  final _tax = TextEditingController(text: '0.08');

  List<Map<String, dynamic>> _suppliers = [];
  String? _supplierId;
  bool _busy = false;
  bool _reviewed = false;
  /// True after on-device OCR filled the text field (still unverified until review).
  bool _fromDeviceOcr = false;
  String? _note;
  String? _error;

  @override
  void initState() {
    super.initState();
    _ocrService = widget.ocrService ?? OcrService();
    _loadSuppliers();
  }

  @override
  void dispose() {
    _ocrService.dispose();
    _ocr.dispose();
    _invoiceNumber.dispose();
    _invoiceDate.dispose();
    _dueDate.dispose();
    _description.dispose();
    _qty.dispose();
    _unit.dispose();
    _tax.dispose();
    super.dispose();
  }

  Future<void> _loadSuppliers() async {
    try {
      final rows = await Session.instance.api.listSuppliers();
      if (!mounted) return;
      setState(() {
        _suppliers = rows;
        if (rows.isNotEmpty) {
          _supplierId = rows.first['id'] as String?;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    }
  }

  Future<void> _captureFrom(ImageSource source) async {
    setState(() {
      _busy = true;
      _error = null;
      _note = null;
    });
    try {
      final text = await _ocrService.pickAndRecognize(source: source);
      if (!mounted) return;
      if (text == null) {
        setState(() => _note = 'Capture cancelled.');
        return;
      }
      if (text.isEmpty) {
        setState(() {
          _error =
              'No text recognized. Try a clearer photo or paste text instead.';
          _fromDeviceOcr = false;
        });
        return;
      }
      setState(() {
        _ocr.text = text;
        _fromDeviceOcr = true;
        _reviewed = false;
        _note =
            'On-device OCR filled the text field. OCR remains unverified '
            '(ocr_verified=false) until you review extracted fields. '
            'No paid OCR.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'OCR failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runExtract() async {
    setState(() {
      _busy = true;
      _error = null;
      _note = null;
      _reviewed = false;
    });
    try {
      final res = await Session.instance.api.extractInvoice(_ocr.text);
      final result = res['result'] as Map<String, dynamic>? ?? {};
      final header = result['header'] as Map<String, dynamic>? ?? {};
      final lines = result['line_items'] as List<dynamic>? ?? [];
      final ocrVerified = result['ocr_verified'] == true;
      setState(() {
        _invoiceNumber.text =
            '${header['invoice_number'] ?? _invoiceNumber.text}';
        if (header['invoice_date'] != null) {
          _invoiceDate.text = '${header['invoice_date']}';
        }
        if (header['due_date'] != null) {
          _dueDate.text = '${header['due_date']}';
        }
        if (lines.isNotEmpty) {
          final ln = lines.first as Map<String, dynamic>;
          _description.text = '${ln['description'] ?? _description.text}';
          if (ln['quantity'] != null) _qty.text = '${ln['quantity']}';
          if (ln['unit_price'] != null) _unit.text = '${ln['unit_price']}';
          if (ln['tax_rate'] != null) _tax.text = '${ln['tax_rate']}';
        }
        final sourceHint = _fromDeviceOcr
            ? 'Source: on-device ML Kit OCR. '
            : 'Source: pasted text. ';
        _note = ocrVerified
            ? 'OCR verified. ${res['explanation'] ?? ''}'
            : '$sourceHint'
                'ocr_verified=false — OCR unverified until you review. '
                '${res['explanation'] ?? ''} '
                'Confidence fields are suggestions only.';
      });
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveDraft() async {
    if (!_reviewed) {
      setState(() => _error = 'Confirm you reviewed extracted fields first.');
      return;
    }
    if (_supplierId == null) {
      setState(() => _error = 'Select a supplier.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final payload = {
        'supplier_id': _supplierId,
        'invoice_number': _invoiceNumber.text.trim().isEmpty
            ? 'INV-MOBILE-${DateTime.now().millisecondsSinceEpoch}'
            : _invoiceNumber.text.trim(),
        'invoice_date': _invoiceDate.text.trim(),
        'due_date': _dueDate.text.trim().isEmpty ? null : _dueDate.text.trim(),
        'currency': 'USD',
        'lines': [
          {
            'description': _description.text.trim(),
            'quantity': _qty.text.trim(),
            'unit_price': _unit.text.trim(),
            'tax_rate': _tax.text.trim(),
          }
        ],
        // Draft only — never auto-approve / auto-submit for review.
        'submit_for_review': false,
      };
      final created = await Session.instance.api.createInvoice(payload);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Draft ${created['invoice_number']} created '
            '(${created['status']})',
          ),
        ),
      );
      Navigator.of(context).pushReplacementNamed('/invoices');
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Capture')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
          Text(
            'Camera or gallery → free on-device ML Kit OCR, or paste text. '
            'Then extract → review → save draft. No paid OCR. No auto-approve.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _ocr,
            maxLines: 8,
            onChanged: (_) {
              if (_fromDeviceOcr) {
                setState(() => _fromDeviceOcr = false);
              }
            },
            decoration: const InputDecoration(
              labelText: 'OCR / document text',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.tonal(
                onPressed: _busy ? null : _runExtract,
                child: const Text('Run extract'),
              ),
              OutlinedButton.icon(
                onPressed: _busy
                    ? null
                    : () => _captureFrom(ImageSource.camera),
                icon: const Icon(Icons.photo_camera_outlined, size: 18),
                label: const Text('Camera'),
              ),
              OutlinedButton.icon(
                onPressed: _busy
                    ? null
                    : () => _captureFrom(ImageSource.gallery),
                icon: const Icon(Icons.photo_library_outlined, size: 18),
                label: const Text('Gallery'),
              ),
            ],
          ),
          if (_note != null) ...[
            const SizedBox(height: 8),
            Text(_note!, style: Theme.of(context).textTheme.bodySmall),
          ],
          const Divider(height: 32),
          DropdownButtonFormField<String>(
            value: _supplierId,
            items: [
              for (final s in _suppliers)
                DropdownMenuItem(
                  value: s['id'] as String?,
                  child: Text('${s['code']} — ${s['name']}'),
                ),
            ],
            onChanged: (v) => setState(() => _supplierId = v),
            decoration: const InputDecoration(
              labelText: 'Supplier',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _invoiceNumber,
            decoration: const InputDecoration(
              labelText: 'Invoice number',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _invoiceDate,
                  decoration: const InputDecoration(
                    labelText: 'Invoice date',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: _dueDate,
                  decoration: const InputDecoration(
                    labelText: 'Due date',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _description,
            decoration: const InputDecoration(
              labelText: 'Line description',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _qty,
                  decoration: const InputDecoration(
                    labelText: 'Qty',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: _unit,
                  decoration: const InputDecoration(
                    labelText: 'Unit price',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: _tax,
                  decoration: const InputDecoration(
                    labelText: 'Tax rate',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ],
          ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: _reviewed,
            onChanged: (v) => setState(() => _reviewed = v ?? false),
            title: const Text(
              'I reviewed extracted fields (OCR unverified otherwise)',
            ),
            subtitle: const Text(
              'Required before save. ocr_verified stays false until review.',
            ),
          ),
          if (_error != null)
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _busy ? null : _saveDraft,
            child: Text(_busy ? 'Saving…' : 'Save capture draft'),
          ),
        ],
        ),
      ),
    );
  }
}
