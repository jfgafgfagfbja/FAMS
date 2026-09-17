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
import '../../widgets/evidence_image.dart';

const _editableStatuses = ['present', 'late', 'absent', 'excused'];

class _RecordsData {
  _RecordsData(this.session, this.roster);

  final SessionDetail session;
  final List<RosterEntry> roster;
}

/// Ket qua 1 phien: trang thai tung SV, anh bang chung, vi tri, sua trang thai kem ly do,
/// lich su sua. P.CTSV/Khoa chi duyet "Có phép".
class SessionRecordsPage extends StatelessWidget {
  const SessionRecordsPage({super.key, required this.sessionId});

  final int sessionId;

  Future<_RecordsData> _load(ApiClient api) async {
    final results = await Future.wait([api.get('/sessions/$sessionId'), api.get('/sessions/$sessionId/roster')]);
    return _RecordsData(
      SessionDetail.fromJson(results[0] as Json),
      (results[1] as List<dynamic>).map((e) => RosterEntry.fromJson(e as Json)).toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final perms = Perms(context.watch<AuthController>().role);
    return AsyncLoader<_RecordsData>(
      load: () => _load(api),
      builder: (context, data, reload) {
        final session = data.session;
        final counts = <String, int>{};
        for (final r in data.roster) {
          counts[r.status ?? 'none'] = (counts[r.status ?? 'none'] ?? 0) + 1;
        }
        return PageBody(
          maxWidth: 1200,
          onRefresh: reload,
          children: [
            Text('${session.classCode} — ${session.subjectName}', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            Wrap(
              spacing: 12,
              runSpacing: 6,
              children: [
                InfoLine(icon: Icons.event, text: '${weekdayLabel(session.sessionDate.weekday - 1)} ${fmtDate(session.sessionDate)} · ${hhmm(session.startTime)}–${hhmm(session.endTime)}'),
                InfoLine(icon: Icons.meeting_room_outlined, text: 'Phòng ${session.room}'),
                if (session.lecturerName != null) InfoLine(icon: Icons.person_outline, text: session.lecturerName!),
                StatusChip(label: session.isOpen ? 'Đang mở' : 'Đã đóng', color: statusColor(session.isOpen ? 'open' : null)),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final status in ['present', 'manual', 'late', 'absent', 'excused'])
                  if ((counts[status] ?? 0) > 0) StatusChip(label: '${attendanceStatusLabel(status)} ${counts[status]}', color: statusColor(status)),
                if ((counts['none'] ?? 0) > 0) StatusChip(label: 'Chưa điểm danh ${counts['none']}', color: statusColor(null)),
                if (session.isOpen && perms.operateAttendance)
                  FilledButton.tonalIcon(
                    onPressed: () => context.push('/sessions/${session.id}/scan'),
                    icon: const Icon(Icons.videocam_outlined),
                    label: const Text('Mở màn hình quét'),
                  ),
                OutlinedButton.icon(
                  onPressed: () => context.push('/reports?class=${session.classId}'),
                  icon: const Icon(Icons.bar_chart_outlined),
                  label: const Text('Báo cáo lớp'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (data.roster.isEmpty)
              const EmptyView(icon: Icons.group_off_outlined, message: 'Lớp này chưa có sinh viên ghi danh.')
            else
              Card(
                clipBehavior: Clip.antiAlias,
                child: Column(
                  children: [
                    for (var i = 0; i < data.roster.length; i++) ...[
                      if (i > 0) const Divider(height: 1),
                      _RecordTile(entry: data.roster[i], session: session, perms: perms, onChanged: reload),
                    ],
                  ],
                ),
              ),
          ],
        );
      },
    );
  }
}

class _RecordTile extends StatelessWidget {
  const _RecordTile({required this.entry, required this.session, required this.perms, required this.onChanged});

  final RosterEntry entry;
  final SessionDetail session;
  final Perms perms;
  final Future<void> Function() onChanged;

  Future<void> _editStatus(BuildContext context) async {
    final newStatus = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const ListTile(title: Text('Chọn trạng thái mới', style: TextStyle(fontWeight: FontWeight.w700))),
            for (final status in _editableStatuses)
              ListTile(
                enabled: status != entry.status,
                leading: Icon(Icons.circle, color: statusColor(status), size: 14),
                title: Text(attendanceStatusLabel(status)),
                onTap: () => Navigator.pop(context, status),
              ),
          ],
        ),
      ),
    );
    if (newStatus == null || !context.mounted) return;
    final ok = await changeRecordStatus(context,
        sessionId: session.id, recordId: entry.recordId!, newStatus: newStatus, title: 'Sửa thành "${attendanceStatusLabel(newStatus)}"');
    if (ok) onChanged();
  }

  Future<void> _showAudits(BuildContext context) async {
    final api = context.read<ApiClient>();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * 0.6,
          child: AsyncLoader<List<AuditEntry>>(
            load: () async {
              final data = await api.get('/sessions/${session.id}/records/${entry.recordId}/audits') as List<dynamic>;
              return data.map((e) => AuditEntry.fromJson(e as Json)).toList();
            },
            builder: (context, audits, _) => ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text('Lịch sử sửa — ${entry.fullName}', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                if (audits.isEmpty) const Text('Chưa có lần sửa nào.'),
                for (final a in audits)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('${attendanceStatusLabel(a.oldStatus)} → ${attendanceStatusLabel(a.newStatus)}'),
                    subtitle: Text('${fmtDateTime(a.changedAt)} · ${a.reason}'),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final details = [
      if (entry.source != null && entry.status != 'absent') sourceLabel(entry.source),
      if (entry.checkedAt != null && entry.status != 'absent') fmtTime(entry.checkedAt),
      if (entry.confidence != null && entry.confidence! > 0) 'khớp ${entry.confidence!.toStringAsFixed(2)}',
    ];
    final hasRecord = entry.recordId != null;
    return ListTile(
      leading: EvidenceImage(path: entry.evidenceImage, size: 46),
      title: Text('${entry.fullName} · ${entry.studentCode}'),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 4),
          StatusChip.attendance(entry.status),
          if (details.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 4), child: Text(details.join(' · '))),
        ],
      ),
      isThreeLine: details.isNotEmpty,
      trailing: Wrap(
        spacing: 2,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          if (entry.latitude != null && entry.longitude != null)
            IconButton(tooltip: 'Vị trí điểm danh', onPressed: () => openMap(entry.latitude!, entry.longitude!), icon: const Icon(Icons.place_outlined)),
          if (hasRecord && perms.editAttendance)
            IconButton(tooltip: 'Lịch sử sửa', onPressed: () => _showAudits(context), icon: const Icon(Icons.history)),
          if (hasRecord && perms.operateAttendance)
            IconButton(tooltip: 'Sửa trạng thái', onPressed: () => _editStatus(context), icon: const Icon(Icons.edit_outlined)),
          if (hasRecord && perms.excuseOnly && entry.status == 'absent')
            TextButton(
              onPressed: () async {
                final ok = await changeRecordStatus(context, sessionId: session.id, recordId: entry.recordId!, newStatus: 'excused', title: 'Duyệt có phép');
                if (ok) onChanged();
              },
              child: const Text('Duyệt có phép'),
            ),
          if (hasRecord && perms.excuseOnly && entry.status == 'excused')
            TextButton(
              onPressed: () async {
                final ok = await changeRecordStatus(context, sessionId: session.id, recordId: entry.recordId!, newStatus: 'absent', title: 'Hủy duyệt có phép');
                if (ok) onChanged();
              },
              child: const Text('Hủy duyệt'),
            ),
          if (!hasRecord && session.isOpen && perms.operateAttendance)
            OutlinedButton(
              onPressed: () async {
                final ok = await runAction(context,
                    () => context.read<ApiClient>().post('/sessions/${session.id}/manual', data: {'student_id': entry.studentId}),
                    success: 'Đã xác nhận tay');
                if (ok) onChanged();
              },
              child: const Text('Xác nhận tay'),
            ),
        ],
      ),
    );
  }
}
