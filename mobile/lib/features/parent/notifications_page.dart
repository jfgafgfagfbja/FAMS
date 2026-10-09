import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Hop thu thong bao cua phu huynh: moi lan con duoc ghi nhan diem danh (co mat, di muon,
/// vang, co phep) co mot muc. Bam vao muc thi danh dau da doc va mo chuyen can cua con.
class NotificationsPage extends StatelessWidget {
  const NotificationsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return AsyncLoader<List<AppNotification>>(
      load: () async => (await api.get('/notifications', query: {'limit': 100}) as List<dynamic>)
          .map((e) => AppNotification.fromJson(e as Json))
          .toList(),
      builder: (context, items, reload) {
        final unread = items.where((n) => !n.isRead).length;
        return PageBody(
          maxWidth: 720,
          onRefresh: reload,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    unread > 0 ? '$unread thông báo chưa đọc' : 'Đã đọc hết thông báo',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                if (unread > 0)
                  TextButton.icon(
                    onPressed: () async {
                      if (await runAction(context, () => api.post('/notifications/read-all'))) reload();
                    },
                    icon: const Icon(Icons.done_all),
                    label: const Text('Đánh dấu đã đọc hết'),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            if (items.isEmpty)
              const EmptyView(
                icon: Icons.notifications_none,
                message: 'Chưa có thông báo nào. Mỗi lần con được điểm danh, thông báo sẽ hiện ở đây.',
              )
            else
              Card(
                clipBehavior: Clip.antiAlias,
                child: Column(
                  children: [
                    for (final n in items) _NotificationTile(item: n, reload: reload),
                  ],
                ),
              ),
          ],
        );
      },
    );
  }
}

class _NotificationTile extends StatelessWidget {
  const _NotificationTile({required this.item, required this.reload});

  final AppNotification item;
  final Future<void> Function() reload;

  static (IconData, Color) _look(String kind) => switch (kind) {
        'attendance_present' => (Icons.check_circle, AppColors.success),
        'attendance_late' => (Icons.schedule, AppColors.warning),
        'attendance_absent' => (Icons.cancel, AppColors.danger),
        'attendance_excused' => (Icons.event_available, AppColors.accent),
        _ => (Icons.notifications, AppColors.neutral),
      };

  Future<void> _open(BuildContext context) async {
    final api = context.read<ApiClient>();
    if (!item.isRead) {
      try {
        await api.post('/notifications/${item.id}/read');
      } catch (_) {
        // Danh dau that bai thi van mo trang - lan sau tai lai se thay con chua doc.
      }
    }
    if (!context.mounted) return;
    final link = item.link;
    if (link != null && link.isNotEmpty) {
      await context.push(link);
    }
    reload();
  }

  @override
  Widget build(BuildContext context) {
    final (icon, color) = _look(item.kind);
    final unread = !item.isRead;
    return ListTile(
      onTap: () => _open(context),
      leading: Icon(icon, color: color),
      title: Text(item.title, style: TextStyle(fontWeight: unread ? FontWeight.w700 : FontWeight.w400)),
      subtitle: Text('${item.body}\n${fmtDateTime(item.createdAt)}'),
      isThreeLine: true,
      trailing: unread
          ? Container(
              width: 10,
              height: 10,
              decoration: const BoxDecoration(color: AppColors.brand, shape: BoxShape.circle),
            )
          : null,
    );
  }
}
