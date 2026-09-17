import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../widgets/common.dart';

class ResetPasswordPage extends StatefulWidget {
  const ResetPasswordPage({super.key, this.email});

  final String? email;

  @override
  State<ResetPasswordPage> createState() => _ResetPasswordPageState();
}

class _ResetPasswordPageState extends State<ResetPasswordPage> {
  final _formKey = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.email);
  final _otp = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _email.dispose();
    _otp.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    final ok = await runAction(
      context,
      () => context.read<ApiClient>().post('/auth/reset-password', data: {
        'email': _email.text.trim(),
        'otp': _otp.text.trim(),
        'new_password': _password.text,
      }),
      success: 'Đặt lại mật khẩu thành công, hãy đăng nhập bằng mật khẩu mới.',
    );
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(leading: BackButton(onPressed: () => context.go('/login')), title: const Text('Đặt lại mật khẩu')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextFormField(
                        controller: _email,
                        decoration: const InputDecoration(labelText: 'Email'),
                        validator: (v) => (v == null || !v.contains('@')) ? 'Nhập email hợp lệ' : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _otp,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        decoration: const InputDecoration(labelText: 'Mã OTP (6 số)'),
                        validator: (v) => RegExp(r'^\d{6}$').hasMatch(v ?? '') ? null : 'Mã OTP gồm 6 chữ số',
                      ),
                      const SizedBox(height: 4),
                      TextFormField(
                        controller: _password,
                        obscureText: true,
                        decoration: const InputDecoration(labelText: 'Mật khẩu mới'),
                        validator: (v) => (v ?? '').length < 8 ? 'Mật khẩu tối thiểu 8 ký tự' : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _confirm,
                        obscureText: true,
                        decoration: const InputDecoration(labelText: 'Nhập lại mật khẩu mới'),
                        validator: (v) => v != _password.text ? 'Mật khẩu nhập lại không khớp' : null,
                      ),
                      const SizedBox(height: 20),
                      FilledButton(onPressed: _loading ? null : _submit, child: const Text('Đặt lại mật khẩu')),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
