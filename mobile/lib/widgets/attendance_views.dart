import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/formatters.dart';
import '../core/theme.dart';
import '../models/models.dart';
import 'common.dart';
import 'evidence_image.dart';

/// Sua trang thai 1 ban ghi diem danh kem ly do bat buoc. Tra true neu thanh cong.
Future<bool> changeRecordStatus(
  BuildContext context, {
  required int sessionId,
  required int recordId,
  required String newStatus,
  required String title,
}) async {
  final reason = await promptText(context, title: title, label: 'Lý do (bắt buộc, lưu vào nhật ký)');
  if (reason == null || !context.mounted) return false;
  return runAction(
    context,
    () => context.read<ApiClient>().patch(
          '/sessions/$sessionId/records/$recordId',
          data: {'status': newStatus, 'reason': reason},
        ),
    success: 'Đã cập nhật: ${attendanceStatusLabel(newStatus)}',
  );
}

/// Chuyen can theo tung lop cua 1 SV (SV tu xem, phu huynh, phong ban).
/// [canExcuse]: hien nut duyet "Có phép"/huy duyet tren tung buoi vang.
class ClassAttendanceList extends StatelessWidget {
  const ClassAttendanceList({super.key, required this.classes, this.canExcuse = false, this.onChanged});

  final List<ClassAttendance> classes;
  final bool canExcuse;
  final VoidCallback? onChanged;

  @override
  Widget build(BuildContext context) {
    if (classes.isEmpty) {
      return const EmptyView(icon: Icons.event_busy_outlined, message: 'Chưa có dữ liệu chuyên cần trong học kỳ này.');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final clazz in classes) ...[
          _ClassCard(clazz: clazz, canExcuse: canExcuse, onChanged: onChanged),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class _ClassCard extends StatelessWidget {
  const _ClassCard({required this.clazz, required this.canExcuse, this.onChanged});

  final ClassAttendance clazz;
  final bool canExcuse;
  final VoidCallback? onChanged;

  @override
  Widget build(BuildContext context) {
    final ratioColor = clazz.warning
        ? AppColors.danger
        : clazz.absentRatio >= clazz.warnRatio * 0.75
            ? AppColors.warning
            : AppColors.success;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        shape: const Border(),
        tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        title: Text('${clazz.classCode} — ${clazz.subjectName}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text('GV: ${clazz.lecturerName} · ${clazz.totalSessions} buổi đã học'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                StatusChip(label: 'Có mặt ${clazz.present + clazz.manual}', color: AppColors.success),
                StatusChip(label: 'Muộn ${clazz.late}', color: AppColors.warning),
                StatusChip(label: 'Vắng ${clazz.absent}', color: AppColors.danger),
                StatusChip(label: 'Có phép ${clazz.excused}', color: AppColors.accent),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: clazz.warnRatio == 0 ? 0 : (clazz.absentRatio / clazz.warnRatio).clamp(0, 1),
                color: ratioColor,
                minHeight: 6,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              clazz.warning
                  ? 'Vắng ${percent(clazz.absentRatio)} — đã vượt ngưỡng ${percent(clazz.warnRatio, digits: 0)}'
                  : 'Vắng ${percent(clazz.absentRatio)} / ngưỡng cảnh báo ${percent(clazz.warnRatio, digits: 0)}',
              style: TextStyle(color: ratioColor, fontSize: 12.5, fontWeight: FontWeight.w600),
            ),
          ],
        ),
        children: [
          if (clazz.sessions.isEmpty)
            const Padding(padding: EdgeInsets.all(16), child: Text('Chưa có buổi học nào đã đóng điểm danh.'))
          else
            for (final session in clazz.sessions.reversed) ...[
              const Divider(height: 1),
              _SessionRow(session: session, canExcuse: canExcuse, onChanged: onChanged),
            ],
        ],
      ),
    );
  }
}

class _SessionRow extends StatelessWidget {
  const _SessionRow({required this.session, required this.canExcuse, this.onChanged});

  final SessionAttendance session;
  final bool canExcuse;
  final VoidCallback? onChanged;

  @override
  Widget build(BuildContext context) {
    final details = [
      if (session.checkedAt != null && session.status != 'absent') 'Ghi nhận ${fmtTime(session.checkedAt)}',
      if (session.source != null && session.status != 'absent') sourceLabel(session.source),
      if (session.confidence != null && session.confidence! > 0) 'Độ khớp ${session.confidence!.toStringAsFixed(2)}',
    ];
    return ListTile(
      leading: EvidenceImage(path: session.evidenceImage, size: 44),
      title: Row(
        children: [
          Text(fmtDate(session.sessionDate), style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(width: 8),
          StatusChip.attendance(session.status),
        ],
      ),
      subtitle: details.isEmpty ? null : Text(details.join(' · ')),
      trailing: Wrap(
        spacing: 4,
        children: [
          if (session.latitude != null && session.longitude != null)
            IconButton(
              tooltip: 'Xem vị trí điểm danh',
              onPressed: () => openMap(session.latitude!, session.longitude!),
              icon: const Icon(Icons.place_outlined),
            ),
          if (canExcuse && session.recordId != null && session.status == 'absent')
            TextButton(
              onPressed: () async {
                final ok = await changeRecordStatus(context,
                    sessionId: session.sessionId, recordId: session.recordId!, newStatus: 'excused', title: 'Duyệt có phép');
                if (ok) onChanged?.call();
              },
              child: const Text('Duyệt có phép'),
            ),
          if (canExcuse && session.recordId != null && session.status == 'excused')
            TextButton(
              onPressed: () async {
                final ok = await changeRecordStatus(context,
                    sessionId: session.sessionId, recordId: session.recordId!, newStatus: 'absent', title: 'Hủy duyệt có phép');
                if (ok) onChanged?.call();
              },
              child: const Text('Hủy duyệt'),
            ),
        ],
      ),
    );
  }
}
