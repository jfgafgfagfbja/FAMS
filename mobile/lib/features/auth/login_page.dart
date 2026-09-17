import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/config.dart';
import '../../core/theme.dart';
import '../../widgets/common.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await context.read<AuthController>().login(_email.text.trim(), _password.text);
    } on ApiException catch (e) {
      setState(() => _error = switch (e.statusCode) {
            401 => 'Sai email hoặc mật khẩu.',
            429 => 'Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau ít phút.',
            _ => e.message,
          });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _configureServer() async {
    final api = context.read<ApiClient>();
    final value = await promptText(
      context,
      title: 'Địa chỉ máy chủ',
      label: 'VD: http://192.168.1.10:8000 (để trống = mặc định)',
      initialValue: api.baseUrl,
      maxLines: 1,
      confirmLabel: 'Lưu',
    );
    if (value == null) return;
    await api.setServerUrl(value == AppConfig.defaultBaseUrl() ? null : value);
    if (mounted) showSnack(context, 'Đã đặt máy chủ: ${api.baseUrl}');
  }

  @override
  Widget build(BuildContext context) {
    final notice = context.watch<AuthController>().notice;
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Form(
                  key: _formKey,
                  child: AutofillGroup(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(color: AppColors.brand, borderRadius: BorderRadius.circular(10)),
                              child: const Text('FA', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 18)),
                            ),
                            const SizedBox(width: 12),
                            const Expanded(
                              child: Text('FAMS', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800)),
                            ),
                            IconButton(
                              tooltip: 'Cấu hình máy chủ',
                              onPressed: _configureServer,
                              icon: const Icon(Icons.settings_ethernet),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Trường Đại học Kiến trúc Đà Nẵng — Hệ thống điểm danh bằng khuôn mặt',
                          style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
                        ),
                        const SizedBox(height: 24),
                        if (notice != null) ...[
                          Text(notice, style: const TextStyle(color: AppColors.warning)),
                          const SizedBox(height: 12),
                        ],
                        TextFormField(
                          controller: _email,
                          keyboardType: TextInputType.emailAddress,
                          autofillHints: const [AutofillHints.email, AutofillHints.username],
                          textInputAction: TextInputAction.next,
                          decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.alternate_email)),
                          validator: (v) => (v == null || !v.contains('@')) ? 'Nhập email hợp lệ' : null,
                        ),
                        const SizedBox(height: 14),
                        TextFormField(
                          controller: _password,
                          obscureText: _obscure,
                          autofillHints: const [AutofillHints.password],
                          onFieldSubmitted: (_) => _submit(),
                          decoration: InputDecoration(
                            labelText: 'Mật khẩu',
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: IconButton(
                              onPressed: () => setState(() => _obscure = !_obscure),
                              icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                            ),
                          ),
                          validator: (v) => (v == null || v.isEmpty) ? 'Nhập mật khẩu' : null,
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          Text(_error!, style: const TextStyle(color: AppColors.danger)),
                        ],
                        const SizedBox(height: 20),
                        FilledButton(
                          onPressed: _loading ? null : _submit,
                          child: _loading
                              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Text('Đăng nhập'),
                        ),
                        const SizedBox(height: 8),
                        TextButton(onPressed: () => context.go('/forgot-password'), child: const Text('Quên mật khẩu?')),
                      ],
                    ),
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
