import 'package:flutter/material.dart';

/// Invoice list/status stub — no API wiring.
class InvoiceListScreen extends StatelessWidget {
  const InvoiceListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Invoices')),
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
              'Invoice list',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            const Text(
              'Searchable invoice statuses, review/flag, and duplicate warnings '
              'will appear after Milestone 2 CRUD and seed data.',
            ),
            const SizedBox(height: 24),
            Card(
              child: ListTile(
                enabled: false,
                title: const Text('No invoices yet'),
                subtitle: const Text('Seed data not loaded'),
                trailing: Chip(
                  label: Text(
                    'Coming Soon',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
