import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

class ChildrenPage extends StatelessWidget {
  const ChildrenPage({super.key});

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<List<Student>>(
      load: () async {
        final data = await context.read<ApiClient>().get('/parents/me/children') as List<dynamic>;
        return data.map((e) => Student.fromJson(e as Json)).toList();
      },
      builder: (context, children, reload) => PageBody(
        maxWidth: 720,
        onRefresh: reload,
        children: [
          if (children.isEmpty)
            const EmptyView(
              icon: Icons.family_restroom_outlined,
              message: 'Tài khoản chưa được liên kết với sinh viên nào. Vui lòng liên hệ Phòng Công tác sinh viên.',
            )
          else
            for (final child in children) ...[
              Card(
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
              ),
              const SizedBox(height: 12),
            ],
        ],
      ),
    );
  }
}
