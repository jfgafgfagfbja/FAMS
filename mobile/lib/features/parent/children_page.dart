import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/dashboard.dart';

class ChildrenPage extends StatelessWidget {
  const ChildrenPage({super.key});

  @override
  Widget build(BuildContext context) {
    final me = context.watch<AuthController>().me;
    return AsyncLoader<(List<Student>, int)>(
      load: () async {
        final api = context.read<ApiClient>();
        final results = await Future.wait([api.get('/parents/me/children'), api.get('/notifications/unread-count')]);
        final children = (results[0] as List<dynamic>).map((e) => Student.fromJson(e as Json)).toList();
        return (children, (results[1] as Json)['count'] as int);
      },
      builder: (context, data, reload) {
        final (children, unread) = data;
        final classCount = children.fold<int>(0, (sum, child) => sum + child.classes.length);
        return PageBody(
          onRefresh: reload,
          children: [
            CardRow(
              flexes: const [7, 5],
              children: [
                ProfileCard(
                  title: 'Thông tin phụ huynh',
                  name: me?.fullName ?? '',
                  onDetail: () => context.go('/account'),
                  fields: [
                    ('Họ tên', me?.fullName ?? ''),
                    ('Email', me?.email ?? ''),
                    ('Vai trò', Roles.label(me?.role ?? Roles.parent)),
                  ],
                ),
                TileColumn(
                  top: DashTile(
                    label: 'Thông báo chưa đọc',
                    value: '$unread',
                    icon: Icons.notifications_none,
                    onTap: () => context.go('/notifications'),
                  ),
                  left: DashTile(label: 'Con đã liên kết', value: '${children.length}', icon: Icons.family_restroom_outlined, tone: TileTone.blue),
                  right: DashTile(label: 'Lớp học phần', value: '$classCount', icon: Icons.class_outlined, tone: TileTone.amber),
                ),
              ],
            ),
            const SizedBox(height: kCardGap),
            if (children.isEmpty)
              const EmptyView(
                icon: Icons.family_restroom_outlined,
                message: 'Tài khoản chưa được liên kết với sinh viên nào. Vui lòng liên hệ Phòng Công tác sinh viên.',
              )
            else
              ResponsiveGrid(
                minItemWidth: 380,
                maxColumns: 2,
                spacing: kCardGap,
                children: [for (final child in children) _ChildCard(child: child)],
              ),
          ],
        );
      },
    );
  }
}

class _ChildCard extends StatelessWidget {
  const _ChildCard({required this.child});

  final Student child;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.push('/children/${child.id}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(radius: 24, child: Text(child.fullName.trim().split(' ').last[0])),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(child.fullName, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                    Text([child.studentCode, child.facultyName, if (child.major.isNotEmpty) child.major]
                        .whereType<String>()
                        .join(' · ')),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        StatusChip(label: '${child.classes.length} lớp học phần', color: Theme.of(context).colorScheme.secondary),
                        StatusChip(
                          label: faceStatusLabel(child.faceStatus),
                          color: statusColor(child.faceStatus == 'none' ? null : child.faceStatus),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }
}
