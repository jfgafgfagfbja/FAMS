import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/attendance_views.dart';
import '../../widgets/common.dart';
import '../../widgets/pickers.dart';
import 'students_page.dart';

/// Ho so + chuyen can chi tiet 1 SV cho can bo; P.CTSV/Khoa/admin duyet co phep tai day.
class StudentDetailPage extends StatefulWidget {
  const StudentDetailPage({super.key, required this.studentId});

  final int studentId;

  @override
  State<StudentDetailPage> createState() => _StudentDetailPageState();
}

class _StudentDetailPageState extends State<StudentDetailPage> {
  String? _semester;

  @override
  Widget build(BuildContext context) {
    final perms = Perms(context.watch<AuthController>().role);
    final canExcuse = perms.excuseOnly || context.read<AuthController>().role == Roles.admin;
    final api = context.read<ApiClient>();
    return AsyncLoader<Student>(
      load: () async => Student.fromJson(await api.get('/students/${widget.studentId}') as Json),
      builder: (context, student, reloadStudent) => PageBody(
        children: [
          SectionCard(
            child: Wrap(
              spacing: 16,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                CircleAvatar(radius: 28, child: Text(student.fullName.trim().split(' ').last[0])),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(student.fullName, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                    Text([student.studentCode, student.email, student.facultyName ?? 'Chưa gán Khoa', if (student.major.isNotEmpty) student.major]
                        .whereType<String>()
                        .join(' · ')),
                    const SizedBox(height: 6),
                    Wrap(spacing: 6, children: [
                      StatusChip(label: faceStatusLabel(student.faceStatus), color: statusColor(student.faceStatus == 'none' ? null : student.faceStatus)),
                      StatusChip(
                        label: student.consentGiven ? 'Đã đồng ý thu thập' : 'Chưa đồng ý thu thập',
                        color: statusColor(student.consentGiven ? 'approved' : null),
                      ),
                    ]),
                  ],
                ),
                if (perms.manageStudents) ...[
                  OutlinedButton.icon(
                    onPressed: () async {
                      if (await editStudent(context, student: student)) reloadStudent();
                    },
                    icon: const Icon(Icons.edit_outlined),
                    label: const Text('Sửa hồ sơ'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => context.push('/enroll-face/${student.id}'),
                    icon: const Icon(Icons.add_a_photo_outlined),
                    label: const Text('Đăng ký khuôn mặt hộ'),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: Text('Chuyên cần', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700))),
              SemesterDropdown(value: _semester, options: semesterOptions(), onChanged: (v) => setState(() => _semester = v)),
            ],
          ),
          const SizedBox(height: 12),
          AsyncLoader<List<ClassAttendance>>(
            loadKey: _semester,
            load: () async {
              final data = await api.get('/students/${student.id}/attendance', query: {'semester': _semester}) as List<dynamic>;
              return data.map((e) => ClassAttendance.fromJson(e as Json)).toList();
            },
            builder: (context, classes, reload) => ClassAttendanceList(classes: classes, canExcuse: canExcuse, onChanged: reload),
          ),
        ],
      ),
    );
  }
}
