import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Invoice AI'),
        actions: [
          TextButton(
            onPressed: () =>
                Navigator.of(context).pushReplacementNamed('/login'),
            child: const Text('Sign out'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Shortcuts',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Capture invoice'),
              subtitle: const Text('Camera / gallery stub — Coming Soon'),
              onTap: () => Navigator.of(context).pushNamed('/capture'),
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.receipt_long_outlined),
              title: const Text('Invoice list'),
              subtitle: const Text('Status list stub — Coming Soon'),
              onTap: () => Navigator.of(context).pushNamed('/invoices'),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Not in this scaffold: OCR extraction, offline drafts, '
            'approvals, payments, or real AI.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
