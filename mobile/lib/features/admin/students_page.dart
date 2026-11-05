import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/form_dialog.dart';
import '../../widgets/paged_list.dart';
import '../../widgets/pickers.dart';

/// Tai danh sach Khoa lam lua chon dropdown trong form.
Future<List<(Object?, String)>> facultyOptions(ApiClient api, {bool allowNone = true}) async {
  final units = await UnitCache.load(api);
  return [
    if (allowNone) (null, '— Chưa gán Khoa —'),
    for (final u in units.where((u) => u.type == 'faculty')) (u.id, u.name),
  ];
}

Future<bool> editStudent(BuildContext context, {Student? student}) async {
  final api = context.read<ApiClient>();
  final faculties = await facultyOptions(api);
  if (!context.mounted) return false;
  final creating = student == null;
  final values = await showFormDialog(
    context,
    title: creating ? 'Thêm sinh viên' : 'Sửa sinh viên',
    fields: [
      if (creating) ...[
        const FieldSpec('student_code', 'MSSV'),
        const FieldSpec('email', 'Email', kind: FieldKind.email),
        const FieldSpec('password', 'Mật khẩu ban đầu', kind: FieldKind.password, minLength: 6),
      ],
      const FieldSpec('full_name', 'Họ tên'),
      const FieldSpec('major', 'Ngành', required: false),
      const FieldSpec('cohort', 'Khóa (năm nhập học)', kind: FieldKind.number, required: false),
      FieldSpec('faculty_id', 'Khoa', kind: FieldKind.dropdown, required: false, options: faculties),
    ],
    initial: student == null
        ? const {'cohort': ''}
        : {'full_name': student.fullName, 'major': student.major, 'cohort': student.cohort, 'faculty_id': student.facultyId},
  );
  if (values == null || !context.mounted) return false;
  return runAction(
    context,
    () => creating ? api.post('/students', data: values) : api.patch('/students/${student.id}', data: values),
    success: creating ? 'Đã thêm sinh viên' : 'Đã cập nhật sinh viên',
  );
}

class StudentsPage extends StatefulWidget {
  const StudentsPage({super.key});

  @override
  State<StudentsPage> createState() => _StudentsPageState();
}

class _StudentsPageState extends State<StudentsPage> {
  int? _facultyId;

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthController>().role;
    final perms = Perms(role);
    final api = context.read<ApiClient>();
    return PageBody(
      children: [
        if (perms.approveExcuse)
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: Text('Chọn sinh viên để xem chuyên cần chi tiết và duyệt đơn xin phép.'),
          ),
        PagedList<Student>(
          filterKey: _facultyId,
          searchHint: 'Tìm theo MSSV hoặc họ tên',
          emptyMessage: 'Không có sinh viên nào trong phạm vi của bạn.',
          emptyIcon: Icons.school_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/students', query: {'q': q, 'faculty_id': _facultyId, 'offset': offset, 'limit': limit});
            return PageResult(page.items.map(Student.fromJson).toList(), page.total);
          },
          filters: [
            if (!Roles.isFaculty(role)) UnitDropdown(value: _facultyId, onChanged: (v) => setState(() => _facultyId = v)),
          ],
          actions: (reload) => [
            if (perms.manageStudents)
              FilledButton.icon(
                onPressed: () async {
                  if (await editStudent(context)) reload();
                },
                icon: const Icon(Icons.person_add_alt),
                label: const Text('Thêm sinh viên'),
              ),
          ],
          itemBuilder: (context, s, reload) => ListTile(
            onTap: () => context.push('/students/${s.id}'),
            leading: CircleAvatar(child: Text(s.fullName.trim().isEmpty ? '?' : s.fullName.trim().split(' ').last[0])),
            title: Text('${s.fullName} · ${s.studentCode}'),
            subtitle: Text([s.facultyName ?? 'Chưa gán Khoa', if (s.major.isNotEmpty) s.major, if (s.cohort > 0) 'K${s.cohort}'].join(' · ')),
            trailing: Wrap(
              spacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                StatusChip(label: faceStatusLabel(s.faceStatus), color: statusColor(s.faceStatus == 'none' ? null : s.faceStatus)),
                if (perms.manageStudents)
                  PopupMenuButton<String>(
                    onSelected: (value) async {
                      if (value == 'edit') {
                        if (await editStudent(context, student: s)) reload();
                      } else if (value == 'face') {
                        context.push('/enroll-face/${s.id}');
                      } else if (value == 'delete') {
                        final ok = await confirmDialog(context,
                            title: 'Xóa sinh viên?', message: 'Xóa ${s.fullName} (${s.studentCode})?', confirmLabel: 'Xóa', destructive: true);
                        if (ok && context.mounted) {
                          if (await runAction(context, () => api.delete('/students/${s.id}'), success: 'Đã xóa')) reload();
                        }
                      }
                    },
                    itemBuilder: (context) => const [
                      PopupMenuItem(value: 'edit', child: Text('Sửa')),
                      PopupMenuItem(value: 'face', child: Text('Đăng ký khuôn mặt hộ')),
                      PopupMenuItem(value: 'delete', child: Text('Xóa')),
                    ],
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
