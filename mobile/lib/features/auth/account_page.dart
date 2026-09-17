import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
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
