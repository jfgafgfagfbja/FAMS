import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/paged_list.dart';
import 'class_detail_page.dart';

/// Toan bo lich hoc trong pham vi (P.DT/admin quan ly; P.CTSV/Khoa xem).
class SchedulesPage extends StatelessWidget {
  const SchedulesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final perms = Perms(context.watch<AuthController>().role);
    final api = context.read<ApiClient>();
    return PageBody(
      children: [
        PagedList<ScheduleItem>(
          searchHint: 'Tìm theo mã lớp, tên môn hoặc phòng',
          emptyMessage: 'Chưa có lịch học nào.',
          emptyIcon: Icons.calendar_month_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/schedules', query: {'q': q, 'offset': offset, 'limit': limit});
            return PageResult(page.items.map(ScheduleItem.fromJson).toList(), page.total);
          },
          actions: (reload) => [
            if (perms.editClasses)
              FilledButton.icon(
                onPressed: () async {
                  final classes = (await api.getPage('/classes')).items.map(ClassInfo.fromJson).toList();
                  if (!context.mounted) return;
                  if (await editSchedule(context, classId: null, classChoices: classes)) reload();
                },
                icon: const Icon(Icons.add),
                label: const Text('Thêm lịch học'),
              ),
          ],
          itemBuilder: (context, s, reload) => ListTile(
            onTap: () => context.push('/classes/${s.classId}'),
            leading: const Icon(Icons.schedule),
            title: Text('${s.classCode} — ${s.subjectName}'),
            subtitle: Text('${weekdayLabel(s.weekday)} · ${hhmm(s.startTime)}–${hhmm(s.endTime)} · ${roomLabel(s.room)}'
                ' · ${s.locationName ?? 'Địa điểm mặc định'}'),
            trailing: perms.editClasses
                ? IconButton(
                    tooltip: 'Sửa',
                    onPressed: () async {
                      if (await editSchedule(context, classId: s.classId, schedule: s)) reload();
                    },
                    icon: const Icon(Icons.edit_outlined),
                  )
                : const Icon(Icons.chevron_right),
          ),
        ),
      ],
    );
  }
}
