import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/evidence_image.dart';

/// Duyet anh khuon mat SV dang ky: doi chieu anh (luu tam), canh bao trung SV khac.
class FaceReviewPage extends StatefulWidget {
  const FaceReviewPage({super.key});

  @override
  State<FaceReviewPage> createState() => _FaceReviewPageState();
}

class _FaceReviewPageState extends State<FaceReviewPage> {
  final Set<int> _busy = {};

  Future<void> _decide(FacePending face, Future<void> Function() reload, {required bool approve}) async {
    final api = context.read<ApiClient>();
    String? reason;
    if (!approve) {
      reason = await promptText(context, title: 'Từ chối ảnh của ${face.fullName}', label: 'Lý do từ chối (SV sẽ thấy)');
      if (reason == null) return;
    }
    setState(() => _busy.add(face.id));
    if (!mounted) return;
    final ok = await runAction(
      context,
      () => approve ? api.patch('/faces/${face.id}/approve') : api.patch('/faces/${face.id}/reject', data: {'reason': reason}),
      success: approve ? 'Đã duyệt ${face.fullName}' : 'Đã từ chối',
    );
    if (mounted) setState(() => _busy.remove(face.id));
    if (ok) reload();
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<List<FacePending>>(
      load: () async {
        final data = await context.read<ApiClient>().get('/faces/pending') as List<dynamic>;
        return data.map((e) => FacePending.fromJson(e as Json)).toList();
      },
      builder: (context, faces, reload) => PageBody(
        maxWidth: 1200,
        onRefresh: reload,
        children: [
          if (faces.isEmpty)
            const EmptyView(icon: Icons.face_retouching_off_outlined, message: 'Không có ảnh khuôn mặt nào đang chờ duyệt.')
          else
            ResponsiveGrid(
              minItemWidth: 260,
              children: [
                for (final face in faces)
                  Card(
                    clipBehavior: Clip.antiAlias,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        AspectRatio(
                          aspectRatio: 1,
                          child: face.sourceImage == null || face.sourceImage!.isEmpty
                              ? const Icon(Icons.account_circle_outlined, size: 64)
                              : EvidenceImage(path: face.sourceImage, size: double.infinity, radius: 0),
                        ),
                        Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(face.fullName, style: const TextStyle(fontWeight: FontWeight.w700)),
                              Text('${face.studentCode} · ${fmtDateTime(face.createdAt)}'),
                              if (face.duplicateWarning) ...[
                                const SizedBox(height: 6),
                                StatusChip(
                                  icon: Icons.warning_amber_rounded,
                                  label: 'Giống SV ${face.duplicateStudentCode} (${face.duplicateSimilarity?.toStringAsFixed(2)})',
                                  color: AppColors.danger,
                                ),
                              ],
                              const SizedBox(height: 10),
                              Row(
                                children: [
                                  Expanded(
                                    child: FilledButton(
                                      onPressed: _busy.contains(face.id) ? null : () => _decide(face, reload, approve: true),
                                      child: const Text('Duyệt'),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: OutlinedButton(
                                      onPressed: _busy.contains(face.id) ? null : () => _decide(face, reload, approve: false),
                                      child: const Text('Từ chối'),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
