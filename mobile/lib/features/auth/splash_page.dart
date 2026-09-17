import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/auth_controller.dart';
import '../../widgets/common.dart';

class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    return Scaffold(
      body: auth.bootstrapError == null
          ? const Center(child: CircularProgressIndicator())
          : ErrorView(message: auth.bootstrapError!, onRetry: auth.bootstrap),
    );
  }
}
