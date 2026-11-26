import 'package:flutter/material.dart';

import 'screens/capture_screen.dart';
import 'screens/home_screen.dart';
import 'screens/invoice_list_screen.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const InvoiceAiApp());
}

class InvoiceAiApp extends StatelessWidget {
  const InvoiceAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Invoice AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1A6B5C),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      initialRoute: '/login',
      routes: {
        '/login': (_) => const LoginScreen(),
        '/home': (_) => const HomeScreen(),
        '/capture': (_) => const CaptureScreen(),
        '/invoices': (_) => const InvoiceListScreen(),
      },
    );
  }
}
