import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Danh sach phien diem danh trong pham vi xem (GV: lop minh day, Khoa: lop Khoa quan ly).
class SessionsPage extends StatefulWidget {
  const SessionsPage({super.key, this.classId, this.embedded = false});

  final int? classId;
  final bool embedded;

  @override
  State<SessionsPage> createState() => _SessionsPageState();
}

class _SessionsPageState extends State<SessionsPage> {
  String? _status;

  Future<List<SessionDetail>> _load() async {
    final data = await context.read<ApiClient>().get('/sessions', query: {
      'status': _status,
      'class_id': widget.classId,
      'limit': 200,
    }) as List<dynamic>;
    return data.map((e) => SessionDetail.fromJson(e as Json)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final perms = Perms(context.watch<AuthController>().role);
    final filters = SegmentedButton<String?>(
      segments: const [
        ButtonSegment(value: null, label: Text('Tất cả')),
        ButtonSegment(value: 'open', label: Text('Đang mở')),
        ButtonSegment(value: 'closed', label: Text('Đã đóng')),
      ],
      selected: {_status},
      onSelectionChanged: (value) => setState(() => _status = value.first),
    );

    Widget list(List<SessionDetail> sessions) => sessions.isEmpty
        ? const EmptyView(icon: Icons.how_to_reg_outlined, message: 'Chưa có phiên điểm danh nào.')
        : Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                for (var i = 0; i < sessions.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  ListTile(
                    onTap: () {
                      final s = sessions[i];
                      context.push(s.isOpen && perms.operateAttendance ? '/sessions/${s.id}/scan' : '/sessions/${s.id}');
                    },
                    leading: CircleAvatar(
                      backgroundColor: statusColor(sessions[i].status).withValues(alpha: 0.12),
                      foregroundColor: statusColor(sessions[i].status),
                      child: Icon(sessions[i].isOpen ? Icons.videocam_outlined : Icons.task_alt),
                    ),
                    title: Text('${sessions[i].classCode} — ${sessions[i].subjectName}'),
                    subtitle: Text(
                      '${weekdayLabel(sessions[i].sessionDate.weekday - 1)} ${fmtDate(sessions[i].sessionDate)} · '
                      '${hhmm(sessions[i].startTime)}–${hhmm(sessions[i].endTime)} · ${roomLabel(sessions[i].room)}'
                      '${sessions[i].lecturerName != null && !perms.operateAttendance ? ' · ${sessions[i].lecturerName}' : ''}',
                    ),
                    trailing: StatusChip(
                      label: sessions[i].isOpen ? 'Đang mở' : 'Đã đóng',
                      color: sessions[i].isOpen ? statusColor('open') : statusColor(null),
                    ),
                  ),
                ],
              ],
            ),
          );

    return AsyncLoader<List<SessionDetail>>(
      loadKey: _status,
      load: _load,
      builder: (context, sessions, reload) {
        if (widget.embedded) {
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Align(alignment: Alignment.centerLeft, child: filters),
            const SizedBox(height: 12),
            list(sessions),
          ]);
        }
        return PageBody(
          onRefresh: reload,
          children: [Align(alignment: Alignment.centerLeft, child: filters), const SizedBox(height: 12), list(sessions)],
        );
      },
    );
  }
}
