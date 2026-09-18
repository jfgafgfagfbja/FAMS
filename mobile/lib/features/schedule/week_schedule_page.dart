import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:printing/printing.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import 'schedule_pdf.dart';

/// Lich hoc/day theo tuan: SV tu diem danh, GV mo phien/vao phien, phong ban xem ket qua.
class WeekSchedulePage extends StatefulWidget {
  const WeekSchedulePage({super.key});

  @override
  State<WeekSchedulePage> createState() => _WeekSchedulePageState();
}

class _WeekSchedulePageState extends State<WeekSchedulePage> {
  DateTime _monday = mondayOf(DateTime.now());
  int? _opening;

  Future<List<WeekSlot>> _load() async {
    final data = await context.read<ApiClient>().get('/schedules/week', query: {'start': isoDate(_monday)}) as List<dynamic>;
    return data.map((e) => WeekSlot.fromJson(e as Json)).toList();
  }

  Future<void> _openSession(WeekSlot slot) async {
    setState(() => _opening = slot.scheduleId);
    try {
      final data = await context.read<ApiClient>().post('/sessions', data: {
        'schedule_id': slot.scheduleId,
        'session_date': isoDate(DateTime.now()),
      }) as Json;
      if (mounted) context.push('/sessions/${data['id']}/scan');
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  /// Xuat thoi khoa bieu tuan ra PDF: web mo hop thoai in cua trinh duyet, Android/iOS mo
  /// man in/chia se cua he dieu hanh.
  Future<void> _print(List<WeekSlot> slots) async {
    final me = context.read<AuthController>().me!;
    final owner = switch (me.role) {
      Roles.student => 'Sinh viên: ${me.fullName}${me.studentCode != null ? ' (${me.studentCode})' : ''}',
      Roles.lecturer => 'Giảng viên: ${me.fullName}${me.lecturerCode != null ? ' (${me.lecturerCode})' : ''}',
      _ => '${Roles.label(me.role)}${me.unitName != null ? ' — ${me.unitName}' : ''}: ${me.fullName}',
    };
    try {
      final fonts = await PdfFonts.load();
      await Printing.layoutPdf(
        name: 'lich-tuan-${isoDate(_monday)}.pdf',
        onLayout: (format) async => Uint8List.fromList(
          await buildWeekSchedulePdf(slots: slots, monday: _monday, owner: owner, fonts: fonts, format: format),
        ),
      );
    } catch (e) {
      if (mounted) showSnack(context, 'Không in được lịch: $e', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthController>().role;
    final today = dateOnly(DateTime.now());
    return AsyncLoader<List<WeekSlot>>(
      loadKey: _monday,
      load: _load,
      builder: (context, slots, reload) {
        final days = List.generate(7, (i) => _monday.add(Duration(days: i)));
        return PageBody(
          onRefresh: reload,
          children: [
            Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: 8,
              runSpacing: 8,
              children: [
                Text('${fmtDate(days.first)} – ${fmtDate(days.last)}', style: Theme.of(context).textTheme.titleMedium),
                IconButton.outlined(
                  tooltip: 'Tuần trước',
                  onPressed: () => setState(() => _monday = _monday.subtract(const Duration(days: 7))),
                  icon: const Icon(Icons.chevron_left),
                ),
                OutlinedButton(onPressed: () => setState(() => _monday = mondayOf(DateTime.now())), child: const Text('Tuần này')),
                IconButton.outlined(
                  tooltip: 'Tuần sau',
                  onPressed: () => setState(() => _monday = _monday.add(const Duration(days: 7))),
                  icon: const Icon(Icons.chevron_right),
                ),
                OutlinedButton.icon(
                  onPressed: slots.isEmpty ? null : () => _print(slots),
                  icon: const Icon(Icons.print_outlined),
                  label: const Text('In lịch'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (slots.isEmpty)
              EmptyView(
                icon: Icons.calendar_today_outlined,
                message: role == Roles.student
                    ? 'Bạn chưa có lịch học trong tuần này.'
                    : role == Roles.lecturer
                        ? 'Bạn chưa có lịch dạy trong tuần này.'
                        : 'Chưa có lịch học trong phạm vi của bạn.',
              )
            else
              for (final day in days)
                if (slots.any((s) => dateOnly(s.date) == day)) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
                    child: Text(
                      '${weekdayLabel(day.weekday - 1)}, ${fmtDate(day)}${day == today ? ' · Hôm nay' : ''}',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: day == today ? Theme.of(context).colorScheme.primary : null,
                      ),
                    ),
                  ),
                  Card(
                    child: Column(
                      children: [
                        for (final slot in slots.where((s) => dateOnly(s.date) == day))
                          _SlotTile(
                            slot: slot,
                            role: role,
                            isToday: day == today,
                            opening: _opening == slot.scheduleId,
                            onOpenSession: () => _openSession(slot),
                          ),
                      ],
                    ),
                  ),
                ],
          ],
        );
      },
    );
  }
}

/// Tieu de man tu diem danh: lop, phong va khu vuc GPS phai dung trong.
String selfCheckinTitle(WeekSlot slot) {
  final area = slot.locationName == null
      ? ''
      : '\nĐiểm danh trong phạm vi ${distanceLabel(slot.locationRadiusM)} quanh ${slot.locationName}';
  return '${slot.classCode} — ${slot.subjectName} · Phòng ${slot.room}$area';
}

class _SlotTile extends StatelessWidget {
  const _SlotTile({
    required this.slot,
    required this.role,
    required this.isToday,
    required this.opening,
    required this.onOpenSession,
  });

  final WeekSlot slot;
  final String role;
  final bool isToday;
  final bool opening;
  final VoidCallback onOpenSession;

  Widget? _trailing(BuildContext context) {
    if (role == Roles.student) {
      if (slot.myStatus != null) return StatusChip.attendance(slot.myStatus);
      if (isToday && slot.sessionStatus == 'open') {
        return FilledButton.icon(
          onPressed: () => context.push('/self-checkin/${slot.sessionId}', extra: selfCheckinTitle(slot)),
          icon: const Icon(Icons.camera_alt_outlined),
          label: const Text('Tự điểm danh'),
        );
      }
      return null;
    }

    if (slot.sessionStatus == 'open') {
      final canScan = Perms(role).operateAttendance;
      return FilledButton.tonalIcon(
        onPressed: () => context.push(canScan ? '/sessions/${slot.sessionId}/scan' : '/sessions/${slot.sessionId}'),
        icon: const Icon(Icons.fiber_manual_record, size: 12),
        label: const Text('Đang điểm danh'),
      );
    }
    if (slot.sessionStatus == 'closed') {
      return OutlinedButton(
        onPressed: () => context.push('/sessions/${slot.sessionId}'),
        child: Text('${slot.presentCount ?? 0}/${slot.totalCount ?? 0} có mặt'),
      );
    }
    if (role == Roles.lecturer && isToday && slot.openFrom != null) {
      if (nowWithin(slot.openFrom!, slot.endTime)) {
        return FilledButton(onPressed: opening ? null : onOpenSession, child: Text(opening ? 'Đang mở…' : 'Mở phiên'));
      }
      if (nowBefore(slot.openFrom!)) return Text('Mở từ ${hhmm(slot.openFrom)}');
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: SizedBox(
        width: 54,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(hhmm(slot.startTime), style: const TextStyle(fontWeight: FontWeight.w700)),
            Text(hhmm(slot.endTime), style: const TextStyle(fontSize: 12)),
          ],
        ),
      ),
      title: Text('${slot.classCode} — ${slot.subjectName}'),
      subtitle: Text(['Phòng ${slot.room}', ?slot.locationName].join(' · ')),
      trailing: _trailing(context),
    );
  }
}
