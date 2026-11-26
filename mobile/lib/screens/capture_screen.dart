import 'package:flutter/material.dart';

/// Camera/gallery capture stub — no OCR or upload.
class CaptureScreen extends StatelessWidget {
  const CaptureScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Capture')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Coming Soon',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Theme.of(context).colorScheme.primary,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Invoice capture',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            const Text(
              'Camera/gallery, on-device text recognition, crop/rotate, and '
              'offline draft save are not implemented in this scaffold.',
            ),
            const SizedBox(height: 24),
            FilledButton.tonal(
              onPressed: null,
              child: const Text('Open camera (disabled)'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: null,
              child: const Text('Pick from gallery (disabled)'),
            ),
          ],
        ),
      ),
    );
  }
}
