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
import '../../widgets/pickers.dart';
import 'students_page.dart';

class LecturersPage extends StatefulWidget {
  const LecturersPage({super.key});

  @override
  State<LecturersPage> createState() => _LecturersPageState();
}

class _LecturersPageState extends State<LecturersPage> {
  int? _facultyId;

  Future<bool> _edit(BuildContext context, {Lecturer? lecturer}) async {
    final api = context.read<ApiClient>();
    final faculties = await facultyOptions(api);
    if (!context.mounted) return false;
    final creating = lecturer == null;
    final values = await showFormDialog(
      context,
      title: creating ? 'Thêm giảng viên' : 'Sửa giảng viên',
      fields: [
        if (creating) ...[
          const FieldSpec('lecturer_code', 'Mã giảng viên'),
          const FieldSpec('email', 'Email', kind: FieldKind.email),
          const FieldSpec('password', 'Mật khẩu ban đầu', kind: FieldKind.password, minLength: 6),
        ],
        const FieldSpec('full_name', 'Họ tên'),
        const FieldSpec('department', 'Bộ môn', required: false),
        FieldSpec('faculty_id', 'Khoa', kind: FieldKind.dropdown, required: false, options: faculties),
      ],
      initial: lecturer == null
          ? const {}
          : {'full_name': lecturer.fullName, 'department': lecturer.department, 'faculty_id': lecturer.facultyId},
    );
    if (values == null || !context.mounted) return false;
    return runAction(
      context,
      () => creating ? api.post('/lecturers', data: values) : api.patch('/lecturers/${lecturer.id}', data: values),
      success: creating ? 'Đã thêm giảng viên' : 'Đã cập nhật giảng viên',
    );
  }

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthController>().role;
    final perms = Perms(role);
    final api = context.read<ApiClient>();
    return PageBody(
      children: [
        PagedList<Lecturer>(
          filterKey: _facultyId,
          searchHint: 'Tìm theo mã hoặc họ tên',
          emptyMessage: 'Không có giảng viên nào.',
          emptyIcon: Icons.co_present_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/lecturers', query: {'q': q, 'faculty_id': _facultyId, 'offset': offset, 'limit': limit});
            return PageResult(page.items.map(Lecturer.fromJson).toList(), page.total);
          },
          filters: [
            if (!Roles.isFaculty(role)) UnitDropdown(value: _facultyId, onChanged: (v) => setState(() => _facultyId = v)),
          ],
          actions: (reload) => [
            if (perms.manageAcademic)
              FilledButton.icon(
                onPressed: () async {
                  if (await _edit(context)) reload();
                },
                icon: const Icon(Icons.person_add_alt),
                label: const Text('Thêm giảng viên'),
              ),
          ],
          itemBuilder: (context, l, reload) => ListTile(
            leading: const CircleAvatar(child: Icon(Icons.co_present_outlined)),
            title: Text('${l.fullName} · ${l.lecturerCode}'),
            subtitle: Text([l.email, l.facultyName ?? 'Chưa gán Khoa', if (l.department.isNotEmpty) l.department].whereType<String>().join(' · ')),
            trailing: perms.manageAcademic
                ? PopupMenuButton<String>(
                    onSelected: (value) async {
                      if (value == 'edit') {
                        if (await _edit(context, lecturer: l)) reload();
                      } else if (value == 'password') {
                        await resetPassword(context, name: l.fullName, path: '/lecturers/${l.id}/reset-password');
                      } else {
                        final ok = await confirmDialog(context,
                            title: 'Xóa giảng viên?', message: 'Xóa ${l.fullName}?', confirmLabel: 'Xóa', destructive: true);
                        if (ok && context.mounted && await runAction(context, () => api.delete('/lecturers/${l.id}'), success: 'Đã xóa')) {
                          reload();
                        }
                      }
                    },
                    itemBuilder: (context) => [
                      const PopupMenuItem(value: 'edit', child: Text('Sửa')),
                      if (perms.resetStaffPassword) const PopupMenuItem(value: 'password', child: Text('Đặt lại mật khẩu')),
                      const PopupMenuItem(value: 'delete', child: Text('Xóa')),
                    ],
                  )
                : null,
          ),
        ),
      ],
    );
  }
}
