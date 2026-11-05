import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/form_dialog.dart';
import '../../widgets/paged_list.dart';
import '../../widgets/reset_password.dart';

class ParentsPage extends StatelessWidget {
  const ParentsPage({super.key});

  Future<bool> _edit(BuildContext context, {ParentInfo? parent}) async {
    final api = context.read<ApiClient>();
    final creating = parent == null;
    final values = await showFormDialog(
      context,
      title: creating ? 'Thêm phụ huynh' : 'Sửa phụ huynh',
      fields: [
        if (creating) ...[
          const FieldSpec('email', 'Email', kind: FieldKind.email),
          const FieldSpec('password', 'Mật khẩu ban đầu', kind: FieldKind.password, minLength: 6),
        ],
        const FieldSpec('full_name', 'Họ tên'),
        const FieldSpec('phone', 'Số điện thoại', required: false),
      ],
      initial: parent == null ? const {} : {'full_name': parent.fullName, 'phone': parent.phone},
    );
    if (values == null || !context.mounted) return false;
    return runAction(
      context,
      () => creating ? api.post('/parents', data: values) : api.patch('/parents/${parent.id}', data: values),
      success: creating ? 'Đã thêm phụ huynh' : 'Đã cập nhật',
    );
  }

  Future<void> _children(BuildContext context, ParentInfo parent, bool canManage, VoidCallback reloadList) async {
    final api = context.read<ApiClient>();
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Con em của ${parent.fullName}'),
        content: SizedBox(
          width: 460,
          child: AsyncLoader<List<Student>>(
            load: () async {
              final data = await api.get('/parents/${parent.id}/children') as List<dynamic>;
              return data.map((e) => Student.fromJson(e as Json)).toList();
            },
            builder: (context, children, reload) => Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (children.isEmpty) const Text('Chưa liên kết sinh viên nào.'),
                for (final s in children)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(s.fullName),
                    subtitle: Text(s.studentCode),
                    trailing: canManage
                        ? IconButton(
                            tooltip: 'Bỏ liên kết',
                            onPressed: () async {
                              if (await runAction(context, () => api.delete('/parents/${parent.id}/children/${s.id}'))) {
                                reload();
                                reloadList();
                              }
                            },
                            icon: const Icon(Icons.link_off),
                          )
                        : null,
                  ),
                if (canManage) ...[
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: () async {
                      final code = await promptText(context, title: 'Liên kết sinh viên', label: 'MSSV', maxLines: 1, confirmLabel: 'Liên kết');
                      if (code == null || !context.mounted) return;
                      if (await runAction(context, () => api.post('/parents/${parent.id}/children', data: {'student_code': code}),
                          success: 'Đã liên kết')) {
                        reload();
                        reloadList();
                      }
                    },
                    icon: const Icon(Icons.link),
                    label: const Text('Liên kết theo MSSV'),
                  ),
                ],
              ],
            ),
          ),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Đóng'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final perms = Perms(context.watch<AuthController>().role);
    final canManage = perms.manageStudents;
    final api = context.read<ApiClient>();
    return PageBody(
      children: [
        PagedList<ParentInfo>(
          searchHint: 'Tìm theo tên hoặc email',
          emptyMessage: 'Chưa có tài khoản phụ huynh.',
          emptyIcon: Icons.family_restroom_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/parents', query: {'q': q, 'offset': offset, 'limit': limit});
            return PageResult(page.items.map(ParentInfo.fromJson).toList(), page.total);
          },
          actions: (reload) => [
            if (canManage)
              FilledButton.icon(
                onPressed: () async {
                  if (await _edit(context)) reload();
                },
                icon: const Icon(Icons.person_add_alt),
                label: const Text('Thêm phụ huynh'),
              ),
          ],
          itemBuilder: (context, p, reload) => ListTile(
            onTap: () => _children(context, p, canManage, reload),
            leading: const CircleAvatar(child: Icon(Icons.family_restroom_outlined)),
            title: Text(p.fullName),
            subtitle: Text([p.email, if (p.phone.isNotEmpty) p.phone, '${p.childCount} con'].join(' · ')),
            trailing: canManage
                ? PopupMenuButton<String>(
                    onSelected: (value) async {
                      if (value == 'edit') {
                        if (await _edit(context, parent: p)) reload();
                      } else if (value == 'password') {
                        await resetPassword(context, name: p.fullName, path: '/parents/${p.id}/reset-password');
                      } else {
                        final ok = await confirmDialog(context,
                            title: 'Xóa phụ huynh?', message: 'Xóa tài khoản ${p.fullName} và các liên kết với con?', confirmLabel: 'Xóa', destructive: true);
                        if (ok && context.mounted && await runAction(context, () => api.delete('/parents/${p.id}'), success: 'Đã xóa')) {
                          reload();
                        }
                      }
                    },
                    itemBuilder: (context) => const [
                      PopupMenuItem(value: 'edit', child: Text('Sửa')),
                      PopupMenuItem(value: 'password', child: Text('Đặt lại mật khẩu')),
                      PopupMenuItem(value: 'delete', child: Text('Xóa')),
                    ],
                  )
                : const Icon(Icons.chevron_right),
          ),
        ),
      ],
    );
  }
}
