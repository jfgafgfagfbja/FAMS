import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

class AccountPage extends StatelessWidget {
  const AccountPage({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final theme = context.watch<ThemeController>();
    final me = auth.me;
    if (me == null) return const SizedBox.shrink();

    final rows = <(String, String)>[
      ('Họ tên', me.fullName),
      ('Email', me.email),
      ('Vai trò', Roles.label(me.role)),
      if (me.studentCode != null) ('MSSV', me.studentCode!),
      if (me.lecturerCode != null) ('Mã giảng viên', me.lecturerCode!),
      if (me.facultyName != null) ('Khoa', me.facultyName!),
      if (me.major != null && me.major!.isNotEmpty) ('Ngành', me.major!),
      if (me.unitName != null) ('Đơn vị', '${me.unitName} (${unitTypeLabel(me.unitType ?? '')})'),
      if (me.position != null && me.position!.isNotEmpty) ('Chức vụ', me.position!),
    ];

    return PageBody(
      maxWidth: 640,
      children: [
        SectionCard(
          title: 'Thông tin tài khoản',
          child: Column(
            children: [
              for (final (label, value) in rows)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 130, child: Text(label, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant))),
                      Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600))),
                    ],
                  ),
                ),
            ],
          ),
        ),
        if (me.role == Roles.parent) ...[
          const SizedBox(height: 16),
          const ParentNotifySettings(),
        ],
        const SizedBox(height: 16),
        SectionCard(
          title: 'Bảo mật',
          child: Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              onPressed: () => showDialog<void>(context: context, builder: (_) => const ChangePasswordDialog()),
              icon: const Icon(Icons.lock_reset),
              label: const Text('Đổi mật khẩu'),
            ),
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Giao diện',
          child: SegmentedButton<ThemeMode>(
            segments: const [
              ButtonSegment(value: ThemeMode.system, label: Text('Theo hệ thống'), icon: Icon(Icons.brightness_auto)),
              ButtonSegment(value: ThemeMode.light, label: Text('Sáng'), icon: Icon(Icons.light_mode_outlined)),
              ButtonSegment(value: ThemeMode.dark, label: Text('Tối'), icon: Icon(Icons.dark_mode_outlined)),
            ],
            selected: {theme.mode},
            onSelectionChanged: (value) => theme.setMode(value.first),
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Kết nối',
          child: InfoLine(icon: Icons.dns_outlined, text: 'Máy chủ: ${context.read<ApiClient>().baseUrl}'),
        ),
        const SizedBox(height: 16),
        FilledButton.tonalIcon(
          onPressed: () async {
            final ok = await confirmDialog(context, title: 'Đăng xuất', message: 'Bạn muốn đăng xuất khỏi FAMS?', confirmLabel: 'Đăng xuất');
            if (ok) await auth.logout();
          },
          icon: const Icon(Icons.logout),
          label: const Text('Đăng xuất'),
        ),
      ],
    );
  }
}

/// Hop thoai doi mat khau. Bat nhap mat khau hien tai (server kiem tra), mat khau moi
/// va nhap lai - kiem tra o day truoc cho do phai goi server roi moi biet sai.
class ChangePasswordDialog extends StatefulWidget {
  const ChangePasswordDialog({super.key});

  @override
  State<ChangePasswordDialog> createState() => _ChangePasswordDialogState();
}

class _ChangePasswordDialogState extends State<ChangePasswordDialog> {
  final _formKey = GlobalKey<FormState>();
  final _current = TextEditingController();
  final _next = TextEditingController();
  final _confirm = TextEditingController();
  bool _show = false;
  bool _saving = false;

  @override
  void dispose() {
    for (final c in [_current, _next, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    final ok = await runAction(
      context,
      () => context.read<ApiClient>().changePassword(_current.text, _next.text),
      success: 'Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất.',
    );
    if (!mounted) return;
    setState(() => _saving = false);
    if (ok) Navigator.pop(context);
  }

  InputDecoration _decoration(String label, {String? helper}) => InputDecoration(
        labelText: label,
        helperText: helper,
        suffixIcon: IconButton(
          tooltip: _show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu',
          icon: Icon(_show ? Icons.visibility_off_outlined : Icons.visibility_outlined),
          onPressed: () => setState(() => _show = !_show),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Đổi mật khẩu'),
      content: SizedBox(
        width: 420,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _current,
                obscureText: !_show,
                autofillHints: const [AutofillHints.password],
                decoration: _decoration('Mật khẩu hiện tại'),
                validator: (v) => (v ?? '').isEmpty ? 'Nhập mật khẩu hiện tại' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _next,
                obscureText: !_show,
                autofillHints: const [AutofillHints.newPassword],
                decoration: _decoration('Mật khẩu mới', helper: 'Ít nhất 8 ký tự'),
                validator: (v) {
                  final value = v ?? '';
                  if (value.length < 8) return 'Mật khẩu mới phải có ít nhất 8 ký tự';
                  if (value == _current.text) return 'Mật khẩu mới phải khác mật khẩu hiện tại';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _confirm,
                obscureText: !_show,
                autofillHints: const [AutofillHints.newPassword],
                decoration: _decoration('Nhập lại mật khẩu mới'),
                validator: (v) => v != _next.text ? 'Hai lần nhập không khớp' : null,
                onFieldSubmitted: (_) => _save(),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: _saving ? null : () => Navigator.pop(context), child: const Text('Hủy')),
        FilledButton(onPressed: _saving ? null : _save, child: Text(_saving ? 'Đang đổi…' : 'Đổi mật khẩu')),
      ],
    );
  }
}

/// Phu huynh tu chon cach nhan thong bao diem danh cua con. Moi lan bat/tat luu ngay.
class ParentNotifySettings extends StatefulWidget {
  const ParentNotifySettings({super.key});

  @override
  State<ParentNotifySettings> createState() => _ParentNotifySettingsState();
}

class _ParentNotifySettingsState extends State<ParentNotifySettings> {
  ParentPreferences? _prefs;
  String? _error;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await context.read<ApiClient>().get('/parents/me/preferences') as Json;
      if (mounted) setState(() => _prefs = ParentPreferences.fromJson(data));
    } catch (e) {
      if (mounted) setState(() => _error = errorText(e));
    }
  }

  Future<void> _update(Map<String, bool> change) async {
    setState(() => _saving = true);
    try {
      final data = await context.read<ApiClient>().patch('/parents/me/preferences', data: change) as Json;
      if (mounted) setState(() => _prefs = ParentPreferences.fromJson(data));
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final prefs = _prefs;
    return SectionCard(
      title: 'Thông báo điểm danh của con',
      child: _error != null
          ? Text(_error!, style: const TextStyle(color: AppColors.danger))
          : prefs == null
              ? const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator()))
              : Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: prefs.notifyPresent,
                      onChanged: _saving ? null : (v) => _update({'notify_present': v}),
                      title: const Text('Báo cả khi con có mặt'),
                      subtitle: const Text('Tắt thì chỉ nhận tin khi con đi muộn hoặc vắng'),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: prefs.notifyEmail,
                      onChanged: _saving ? null : (v) => _update({'notify_email': v}),
                      title: const Text('Gửi qua email'),
                      subtitle: Text(prefs.emailAvailable
                          ? 'Thông báo vẫn luôn có trong mục Thông báo của ứng dụng'
                          : 'Máy chủ chưa bật gửi email — hiện chỉ nhận thông báo trong ứng dụng'),
                    ),
                  ],
                ),
    );
  }
}
