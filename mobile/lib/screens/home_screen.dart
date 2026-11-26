import 'package:flutter/material.dart';

import '../services/session.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = Session.instance;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Invoice AI'),
        actions: [
          TextButton(
            onPressed: () {
              session.clear();
              Navigator.of(context).pushReplacementNamed('/login');
            },
            child: const Text('Sign out'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            session.email ?? 'Signed in',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(
            'Role: ${session.role ?? '—'}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          Text(
            'Shortcuts',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Capture invoice'),
              subtitle: const Text(
                'Paste OCR text → extract assist → create draft',
              ),
              onTap: () => Navigator.of(context).pushNamed('/capture'),
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.receipt_long_outlined),
              title: const Text('Invoice list'),
              subtitle: const Text('Live statuses from /api/v1/invoices'),
              onTap: () => Navigator.of(context).pushNamed('/invoices'),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'On-device camera OCR is optional (free ML Kit). This MVP uses '
            'pasted/demo text + the same DemoAIProvider extract as web. '
            'No paid OCR.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
