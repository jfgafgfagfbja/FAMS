import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../widgets/common.dart';

class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({super.key});

  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  final _email = TextEditingController();
  bool _loading = false;
  bool _sent = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_email.text.contains('@')) {
      showSnack(context, 'Nhập email hợp lệ', error: true);
      return;
    }
    setState(() => _loading = true);
    final ok = await runAction(context, () => context.read<ApiClient>().post('/auth/forgot-password', data: {'email': _email.text.trim()}));
    if (mounted) {
      setState(() {
        _loading = false;
        _sent = ok;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(leading: BackButton(onPressed: () => context.go('/login')), title: const Text('Quên mật khẩu')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Nhập email tài khoản. Nếu email tồn tại, hệ thống sẽ gửi mã OTP (hiệu lực 10 phút) để đặt lại mật khẩu.'),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.alternate_email)),
                      onSubmitted: (_) => _submit(),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(onPressed: _loading ? null : _submit, child: const Text('Gửi mã OTP')),
                    if (_sent) ...[
                      const SizedBox(height: 16),
                      const Text('Nếu email tồn tại trong hệ thống, mã OTP đã được gửi. Hãy kiểm tra hộp thư.'),
                      const SizedBox(height: 8),
                      OutlinedButton(
                        onPressed: () => context.go(Uri(path: '/reset-password', queryParameters: {'email': _email.text.trim()}).toString()),
                        child: const Text('Nhập mã OTP'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
