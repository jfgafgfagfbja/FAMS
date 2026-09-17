import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../office/overview_page.dart';
import '../parent/children_page.dart';

/// Trang chu theo vai tro.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthController>().role;
    return switch (role) {
      Roles.student => const _StudentHome(),
      Roles.lecturer => const _LecturerHome(),
      Roles.parent => const ChildrenPage(),
      Roles.admin => const OverviewPage(showAdminShortcuts: true),
      _ => const OverviewPage(),
    };
  }
}

// ---------------- Sinh vien ----------------

class _StudentHomeData {
  _StudentHomeData(this.today, this.attendance);

  final List<WeekSlot> today;
  final List<ClassAttendance> attendance;
}

class _StudentHome extends StatelessWidget {
  const _StudentHome();

  Future<_StudentHomeData> _load(BuildContext context) async {
    final api = context.read<ApiClient>();
    final auth = context.read<AuthController>();
    final now = DateTime.now();
    final results = await Future.wait([
      api.get('/schedules/week', query: {'start': isoDate(now)}),
      api.get('/students/me/attendance'),
      auth.reloadMe(),
    ]);
    final today = (results[0] as List<dynamic>)
        .map((e) => WeekSlot.fromJson(e as Json))
        .where((slot) => dateOnly(slot.date) == dateOnly(now))
        .toList();
    final attendance = (results[1] as List<dynamic>).map((e) => ClassAttendance.fromJson(e as Json)).toList();
    return _StudentHomeData(today, attendance);
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<_StudentHomeData>(
      load: () => _load(context),
      builder: (context, data, reload) {
        final me = context.watch<AuthController>().me!;
        final warnings = data.attendance.where((c) => c.warning).toList();
        return PageBody(
          onRefresh: reload,
          children: [
            SectionCard(
              child: Row(
                children: [
                  CircleAvatar(radius: 26, child: Text(me.fullName.isEmpty ? '?' : me.fullName.trim().split(' ').last[0])),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Xin chào, ${me.fullName}', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                        Text([me.studentCode, me.facultyName].whereType<String>().join(' · ')),
                        const SizedBox(height: 6),
                        StatusChip(
                          label: faceStatusLabel(me.faceStatus),
                          color: statusColor(me.faceStatus == 'none' ? null : me.faceStatus),
                        ),
                      ],
                    ),
                  ),
                  if (me.faceStatus != 'approved')
                    FilledButton.tonal(onPressed: () => context.go('/face'), child: const Text('Đăng ký khuôn mặt')),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SectionCard(
              title: 'Hôm nay (${weekdayLabel(DateTime.now().weekday - 1)}, ${fmtDate(DateTime.now())})',
              trailing: TextButton(onPressed: () => context.go('/schedule'), child: const Text('Cả tuần')),
              child: data.today.isEmpty
                  ? const EmptyView(icon: Icons.free_breakfast_outlined, message: 'Hôm nay bạn không có lịch học.')
                  : Column(
                      children: [
                        for (final slot in data.today)
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text('${slot.classCode} — ${slot.subjectName}'),
                            subtitle: Text('${hhmm(slot.startTime)}–${hhmm(slot.endTime)} · Phòng ${slot.room}'),
                            trailing: slot.myStatus != null
                                ? StatusChip.attendance(slot.myStatus)
                                : slot.sessionStatus == 'open'
                                    ? FilledButton.icon(
                                        onPressed: () => context.push('/self-checkin/${slot.sessionId}',
                                            extra: '${slot.classCode} — ${slot.subjectName} · Phòng ${slot.room}'),
                                        icon: const Icon(Icons.camera_alt_outlined),
                                        label: const Text('Tự điểm danh'),
                                      )
                                    : Text(slot.sessionStatus == 'closed' ? 'Đã đóng' : 'Chưa mở phiên'),
                          ),
                      ],
                    ),
            ),
            const SizedBox(height: 16),
            SectionCard(
              title: 'Chuyên cần học kỳ',
              trailing: TextButton(onPressed: () => context.go('/my-attendance'), child: const Text('Chi tiết')),
              child: data.attendance.isEmpty
                  ? const Text('Chưa có dữ liệu chuyên cần.')
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (warnings.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: StatusChip(
                              icon: Icons.warning_amber_rounded,
                              label: '${warnings.length} lớp vượt ngưỡng vắng — nguy cơ cấm thi',
                              color: AppColors.danger,
                            ),
                          ),
                        for (final c in data.attendance)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${c.classCode} — ${c.subjectName}', style: const TextStyle(fontWeight: FontWeight.w600)),
                                const SizedBox(height: 4),
                                LinearProgressIndicator(
                                  value: c.warnRatio == 0 ? 0 : (c.absentRatio / c.warnRatio).clamp(0, 1),
                                  color: c.warning ? AppColors.danger : AppColors.success,
                                  minHeight: 6,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                const SizedBox(height: 2),
                                Text('Vắng ${c.absent}/${c.totalSessions} buổi (${percent(c.absentRatio)})', style: const TextStyle(fontSize: 12.5)),
                              ],
                            ),
                          ),
                      ],
                    ),
            ),
          ],
        );
      },
    );
  }
}

// ---------------- Giang vien ----------------

class _LecturerHomeData {
  _LecturerHomeData(this.today, this.openSessions, this.warnedStudents);

  final List<TodaySchedule> today;
  final List<SessionDetail> openSessions;
  final int warnedStudents;
}

class _LecturerHome extends StatefulWidget {
  const _LecturerHome();

  @override
  State<_LecturerHome> createState() => _LecturerHomeState();
}

class _LecturerHomeState extends State<_LecturerHome> {
  int? _opening;

  Future<_LecturerHomeData> _load() async {
    final api = context.read<ApiClient>();
    final auth = context.read<AuthController>();
    await auth.reloadMe();
    final results = await Future.wait([
      api.get('/lecturers/me/today-schedules'),
      api.get('/sessions', query: {'status': 'open'}),
    ]);
    final warned = <int>{};
    for (final c in auth.me?.classes ?? const <ClassBrief>[]) {
      try {
        final rows = await api.get('/reports/attendance/warnings', query: {'class_id': c.id}) as List<dynamic>;
        warned.addAll(rows.map((r) => (r as Json)['student_id'] as int));
      } catch (_) {}
    }
    return _LecturerHomeData(
      (results[0] as List<dynamic>).map((e) => TodaySchedule.fromJson(e as Json)).toList(),
      (results[1] as List<dynamic>).map((e) => SessionDetail.fromJson(e as Json)).toList(),
      warned.length,
    );
  }

  Future<void> _openSession(TodaySchedule schedule) async {
    setState(() => _opening = schedule.scheduleId);
    try {
      final data = await context.read<ApiClient>().post('/sessions', data: {
        'schedule_id': schedule.scheduleId,
        'session_date': isoDate(DateTime.now()),
      }) as Json;
      if (mounted) context.push('/sessions/${data['id']}/scan');
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  Widget _action(TodaySchedule s) {
    if (s.sessionId != null) {
      return s.sessionStatus == 'open'
          ? FilledButton.icon(
              onPressed: () => context.push('/sessions/${s.sessionId}/scan'),
              icon: const Icon(Icons.videocam_outlined),
              label: const Text('Vào điểm danh'),
            )
          : OutlinedButton(onPressed: () => context.push('/sessions/${s.sessionId}'), child: const Text('Xem kết quả'));
    }
    if (nowWithin(s.openFrom, s.endTime)) {
      return FilledButton(
        onPressed: _opening == s.scheduleId ? null : () => _openSession(s),
        child: Text(_opening == s.scheduleId ? 'Đang mở…' : 'Mở phiên'),
      );
    }
    return Text(nowAfter(s.endTime) ? 'Đã kết thúc' : 'Mở từ ${hhmm(s.openFrom)}');
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<_LecturerHomeData>(
      load: _load,
      builder: (context, data, reload) {
        final me = context.watch<AuthController>().me!;
        return PageBody(
          onRefresh: reload,
          children: [
            Text('Xin chào, ${me.fullName}', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
            Text([me.lecturerCode, me.facultyName].whereType<String>().join(' · ')),
            const SizedBox(height: 16),
            ResponsiveGrid(
              children: [
                StatCard(label: 'Buổi dạy hôm nay', value: '${data.today.length}', icon: Icons.event_available_outlined, onTap: () => context.go('/schedule')),
                StatCard(label: 'Phiên đang mở', value: '${data.openSessions.length}', icon: Icons.how_to_reg_outlined, onTap: () => context.go('/sessions')),
                StatCard(
                  label: 'SV vượt ngưỡng vắng',
                  value: '${data.warnedStudents}',
                  icon: Icons.warning_amber_rounded,
                  color: data.warnedStudents > 0 ? AppColors.danger : AppColors.success,
                  onTap: () => context.go('/reports'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SectionCard(
              title: 'Lịch dạy hôm nay',
              child: data.today.isEmpty
                  ? const EmptyView(icon: Icons.free_breakfast_outlined, message: 'Hôm nay không có lịch dạy.')
                  : Column(
                      children: [
                        for (final s in data.today)
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text('${s.classCode} — ${s.subjectName}'),
                            subtitle: Text('${hhmm(s.startTime)}–${hhmm(s.endTime)} · Phòng ${s.room}'),
                            trailing: _action(s),
                          ),
                      ],
                    ),
            ),
          ],
        );
      },
    );
  }
}
