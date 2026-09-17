import 'dart:convert';

import 'package:file_picker/file_picker.dart';
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
import '../lecturer/sessions_page.dart';
import 'classes_page.dart';

class _ClassData {
  _ClassData(this.clazz, this.students, this.schedules);

  final ClassInfo clazz;
  final List<Student> students;
  final List<ScheduleItem> schedules;
}

/// Chi tiet lop: sinh vien (ghi danh/huy/nhap CSV), lich hoc, phien diem danh.
class ClassDetailPage extends StatelessWidget {
  const ClassDetailPage({super.key, required this.classId});

  final int classId;

  Future<_ClassData> _load(ApiClient api) async {
    final results = await Future.wait([
      api.get('/classes/$classId'),
      api.get('/classes/$classId/students'),
      api.get('/classes/$classId/schedules'),
    ]);
    return _ClassData(
      ClassInfo.fromJson(results[0] as Json),
      (results[1] as List<dynamic>).map((e) => Student.fromJson(e as Json)).toList(),
      (results[2] as List<dynamic>).map((e) => ScheduleItem.fromJson(e as Json)).toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final perms = Perms(context.watch<AuthController>().role);
    return AsyncLoader<_ClassData>(
      load: () => _load(api),
      builder: (context, data, reload) {
        final c = data.clazz;
        return DefaultTabController(
          length: 3,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Material(
                color: Theme.of(context).colorScheme.surface,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 12,
                        runSpacing: 8,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text('${c.classCode} — ${c.subjectName}', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                          if (perms.manageAcademic) ...[
                            OutlinedButton.icon(
                              onPressed: () async {
                                if (await editClass(context, clazz: c)) reload();
                              },
                              icon: const Icon(Icons.edit_outlined),
                              label: const Text('Sửa'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () async {
                                final ok = await confirmDialog(context,
                                    title: 'Xóa lớp học phần?',
                                    message: 'Chỉ xóa được khi lớp chưa có sinh viên và lịch học.',
                                    confirmLabel: 'Xóa',
                                    destructive: true);
                                if (ok && context.mounted && await runAction(context, () => api.delete('/classes/${c.id}'), success: 'Đã xóa lớp')) {
                                  if (context.mounted) context.go('/classes');
                                }
                              },
                              icon: const Icon(Icons.delete_outline),
                              label: const Text('Xóa'),
                            ),
                          ],
                          OutlinedButton.icon(
                            onPressed: () => context.push('/reports?class=${c.id}'),
                            icon: const Icon(Icons.bar_chart_outlined),
                            label: const Text('Báo cáo'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text([
                        formatSemester(c.semester),
                        if (c.lecturerName != null) 'GV: ${c.lecturerName}',
                        c.facultyName ?? 'Chưa gán Khoa',
                      ].join(' · ')),
                      TabBar(
                        isScrollable: true,
                        tabAlignment: TabAlignment.start,
                        tabs: [
                          Tab(text: 'Sinh viên (${data.students.length})'),
                          Tab(text: 'Lịch học (${data.schedules.length})'),
                          const Tab(text: 'Phiên điểm danh'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              Expanded(
                child: TabBarView(
                  children: [
                    _StudentsTab(data: data, perms: perms, reload: reload),
                    _SchedulesTab(data: data, perms: perms, reload: reload),
                    ListView(padding: const EdgeInsets.all(16), children: [SessionsPage(classId: c.id, embedded: true)]),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StudentsTab extends StatelessWidget {
  const _StudentsTab({required this.data, required this.perms, required this.reload});

  final _ClassData data;
  final Perms perms;
  final Future<void> Function() reload;

  Future<void> _enrollOne(BuildContext context) async {
    final api = context.read<ApiClient>();
    final code = await promptText(context, title: 'Ghi danh sinh viên', label: 'MSSV', maxLines: 1, confirmLabel: 'Ghi danh');
    if (code == null || !context.mounted) return;
    final page = await api.getPage('/students', query: {'q': code});
    final match = page.items.map(Student.fromJson).where((s) => s.studentCode.toLowerCase() == code.toLowerCase());
    if (!context.mounted) return;
    if (match.isEmpty) {
      showSnack(context, 'Không tìm thấy sinh viên MSSV $code', error: true);
      return;
    }
    if (await runAction(context, () => api.post('/classes/${data.clazz.id}/enroll/${match.first.id}'), success: 'Đã ghi danh ${match.first.fullName}')) {
      reload();
    }
  }

  /// CSV: moi dong 1 MSSV (cot dau tien), dong tieu de khong phai MSSV se bi bo qua.
  Future<void> _importCsv(BuildContext context) async {
    final api = context.read<ApiClient>();
    final files = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: const ['csv', 'txt']);
    if (files.isEmpty || !context.mounted) return;
    final content = utf8.decode(await files.first.readAsBytes(), allowMalformed: true);
    final codes = content
        .split(RegExp(r'\r?\n'))
        .map((line) => line.split(RegExp('[,;\t]')).first.trim().replaceAll('"', ''))
        .where((code) => code.isNotEmpty)
        .toSet();
    final all = (await api.getPage('/students')).items.map(Student.fromJson).toList();
    final byCode = {for (final s in all) s.studentCode.toLowerCase(): s};
    final enrolled = {for (final s in data.students) s.id};
    var added = 0;
    final missing = <String>[];
    for (final code in codes) {
      final student = byCode[code.toLowerCase()];
      if (student == null) {
        missing.add(code);
        continue;
      }
      if (enrolled.contains(student.id)) continue;
      try {
        await api.post('/classes/${data.clazz.id}/enroll/${student.id}');
        added++;
      } catch (_) {
        missing.add(code);
      }
    }
    if (!context.mounted) return;
    showSnack(context, 'Đã ghi danh $added sinh viên${missing.isEmpty ? '' : '. Bỏ qua ${missing.length} dòng: ${missing.take(5).join(', ')}'}');
    reload();
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (perms.manageAcademic)
          Wrap(spacing: 12, runSpacing: 8, children: [
            FilledButton.icon(onPressed: () => _enrollOne(context), icon: const Icon(Icons.person_add_alt), label: const Text('Ghi danh')),
            OutlinedButton.icon(onPressed: () => _importCsv(context), icon: const Icon(Icons.upload_file), label: const Text('Nhập CSV (MSSV)')),
          ]),
        const SizedBox(height: 12),
        if (data.students.isEmpty)
          const EmptyView(icon: Icons.group_off_outlined, message: 'Lớp chưa có sinh viên ghi danh.')
        else
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                for (final s in data.students)
                  ListTile(
                    onTap: perms.viewStudents ? () => context.push('/students/${s.id}') : null,
                    title: Text('${s.fullName} · ${s.studentCode}'),
                    subtitle: Text(faceStatusLabel(s.faceStatus)),
                    trailing: Wrap(spacing: 4, children: [
                      if (perms.enrollFaceForOthers && s.faceStatus != 'approved')
                        IconButton(
                          tooltip: 'Đăng ký khuôn mặt hộ',
                          onPressed: () => context.push('/enroll-face/${s.id}'),
                          icon: const Icon(Icons.add_a_photo_outlined),
                        ),
                      if (perms.manageAcademic)
                        IconButton(
                          tooltip: 'Hủy ghi danh',
                          onPressed: () async {
                            final ok = await confirmDialog(context,
                                title: 'Hủy ghi danh?', message: 'Hủy ghi danh ${s.fullName} khỏi lớp?', confirmLabel: 'Hủy ghi danh', destructive: true);
                            if (ok && context.mounted && await runAction(context, () => api.delete('/classes/${data.clazz.id}/enroll/${s.id}'))) {
                              reload();
                            }
                          },
                          icon: const Icon(Icons.person_remove_outlined),
                        ),
                    ]),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

Future<bool> editSchedule(BuildContext context, {required int? classId, ScheduleItem? schedule, List<ClassInfo>? classChoices}) async {
  final api = context.read<ApiClient>();
  final creating = schedule == null;
  final values = await showFormDialog(
    context,
    title: creating ? 'Thêm lịch học' : 'Sửa lịch học',
    fields: [
      if (creating && classId == null)
        FieldSpec('class_id', 'Lớp học phần', kind: FieldKind.dropdown,
            options: [for (final c in classChoices ?? const <ClassInfo>[]) (c.id, '${c.classCode} — ${c.subjectName}')]),
      FieldSpec('weekday', 'Thứ', kind: FieldKind.dropdown, options: [for (var i = 0; i < 7; i++) (i, weekdayLabel(i))]),
      const FieldSpec('start_time', 'Giờ bắt đầu', kind: FieldKind.time),
      const FieldSpec('end_time', 'Giờ kết thúc', kind: FieldKind.time),
      const FieldSpec('room', 'Phòng'),
    ],
    initial: schedule == null
        ? const {'weekday': 0, 'start_time': '07:00:00', 'end_time': '09:00:00'}
        : {'weekday': schedule.weekday, 'start_time': schedule.startTime, 'end_time': schedule.endTime, 'room': schedule.room},
  );
  if (values == null || !context.mounted) return false;
  if ((values['start_time'] as String).compareTo(values['end_time'] as String) >= 0) {
    showSnack(context, 'Giờ bắt đầu phải trước giờ kết thúc', error: true);
    return false;
  }
  return runAction(
    context,
    () => creating
        ? api.post('/classes/schedules', data: {'class_id': classId ?? values['class_id'], ...values})
        : api.patch('/classes/schedules/${schedule.id}', data: values),
    success: creating ? 'Đã thêm lịch học' : 'Đã cập nhật lịch học',
  );
}

class _SchedulesTab extends StatelessWidget {
  const _SchedulesTab({required this.data, required this.perms, required this.reload});

  final _ClassData data;
  final Perms perms;
  final Future<void> Function() reload;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (perms.manageAcademic)
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: () async {
                if (await editSchedule(context, classId: data.clazz.id)) reload();
              },
              icon: const Icon(Icons.add),
              label: const Text('Thêm lịch học'),
            ),
          ),
        const SizedBox(height: 12),
        if (data.schedules.isEmpty)
          const EmptyView(icon: Icons.event_busy_outlined, message: 'Lớp chưa có lịch học.')
        else
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                for (final s in data.schedules)
                  ListTile(
                    leading: const Icon(Icons.schedule),
                    title: Text('${weekdayLabel(s.weekday)} · ${hhmm(s.startTime)}–${hhmm(s.endTime)}'),
                    subtitle: Text('Phòng ${s.room}'),
                    trailing: perms.manageAcademic
                        ? Wrap(children: [
                            IconButton(
                              tooltip: 'Sửa',
                              onPressed: () async {
                                if (await editSchedule(context, classId: data.clazz.id, schedule: s)) reload();
                              },
                              icon: const Icon(Icons.edit_outlined),
                            ),
                            IconButton(
                              tooltip: 'Xóa',
                              onPressed: () async {
                                final ok = await confirmDialog(context,
                                    title: 'Xóa lịch học?', message: 'Chỉ xóa được khi lịch chưa có phiên điểm danh.', confirmLabel: 'Xóa', destructive: true);
                                if (ok && context.mounted && await runAction(context, () => api.delete('/classes/schedules/${s.id}'), success: 'Đã xóa')) {
                                  reload();
                                }
                              },
                              icon: const Icon(Icons.delete_outline),
                            ),
                          ])
                        : null,
                  ),
              ],
            ),
          ),
      ],
    );
  }
}
