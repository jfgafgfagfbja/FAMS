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
import 'students_page.dart';

Future<bool> editClass(BuildContext context, {ClassInfo? clazz}) async {
  final api = context.read<ApiClient>();
  final lecturersPage = await api.getPage('/lecturers');
  final faculties = await facultyOptions(api);
  if (!context.mounted) return false;
  final lecturers = lecturersPage.items.map(Lecturer.fromJson).toList();
  final creating = clazz == null;
  final values = await showFormDialog(
    context,
    title: creating ? 'Thêm lớp học phần' : 'Sửa lớp học phần',
    fields: [
      const FieldSpec('class_code', 'Mã lớp học phần'),
      const FieldSpec('subject_name', 'Tên môn học'),
      FieldSpec('lecturer_id', 'Giảng viên phụ trách', kind: FieldKind.dropdown,
          options: [for (final l in lecturers) (l.id, '${l.fullName} (${l.lecturerCode})')]),
      FieldSpec('semester', 'Học kỳ', kind: FieldKind.dropdown,
          options: [for (final s in {...semesterOptions(), ?clazz?.semester}) (s, formatSemester(s))]),
      FieldSpec('faculty_id', 'Khoa quản lý', kind: FieldKind.dropdown, required: false, options: faculties),
    ],
    initial: clazz == null
        ? {'semester': '${DateTime.now().year}.1'}
        : {
            'class_code': clazz.classCode,
            'subject_name': clazz.subjectName,
            'lecturer_id': clazz.lecturerId,
            'semester': clazz.semester,
            'faculty_id': clazz.facultyId,
          },
  );
  if (values == null || !context.mounted) return false;
  return runAction(
    context,
    () => creating ? api.post('/classes', data: values) : api.patch('/classes/${clazz.id}', data: values),
    success: creating ? 'Đã thêm lớp học phần' : 'Đã cập nhật lớp học phần',
  );
}

class ClassesPage extends StatefulWidget {
  const ClassesPage({super.key});

  @override
  State<ClassesPage> createState() => _ClassesPageState();
}

class _ClassesPageState extends State<ClassesPage> {
  int? _facultyId;
  String? _semester;

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthController>().role;
    final perms = Perms(role);
    final api = context.read<ApiClient>();
    return PageBody(
      children: [
        PagedList<ClassInfo>(
          filterKey: (_facultyId, _semester),
          searchHint: 'Tìm theo mã lớp hoặc tên môn',
          emptyMessage: 'Không có lớp học phần nào trong phạm vi của bạn.',
          emptyIcon: Icons.class_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/classes', query: {
              'q': q,
              'faculty_id': _facultyId,
              'semester': _semester,
              'offset': offset,
              'limit': limit,
            });
            return PageResult(page.items.map(ClassInfo.fromJson).toList(), page.total);
          },
          filters: [
            SemesterDropdown(value: _semester, options: semesterOptions(), onChanged: (v) => setState(() => _semester = v)),
            if (role != Roles.faculty && role != Roles.lecturer)
              UnitDropdown(value: _facultyId, onChanged: (v) => setState(() => _facultyId = v)),
          ],
          actions: (reload) => [
            if (perms.manageAcademic)
              FilledButton.icon(
                onPressed: () async {
                  if (await editClass(context)) reload();
                },
                icon: const Icon(Icons.add),
                label: const Text('Thêm lớp'),
              ),
          ],
          itemBuilder: (context, c, reload) => ListTile(
            onTap: () => context.push('/classes/${c.id}'),
            leading: const CircleAvatar(child: Icon(Icons.class_outlined)),
            title: Text('${c.classCode} — ${c.subjectName}'),
            subtitle: Text([
              formatSemester(c.semester),
              if (c.lecturerName != null) 'GV: ${c.lecturerName}',
              c.facultyName ?? 'Chưa gán Khoa',
              '${c.studentCount ?? 0} SV',
            ].join(' · ')),
            trailing: const Icon(Icons.chevron_right),
          ),
        ),
      ],
    );
  }
}
