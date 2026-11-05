import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../models/models.dart';
import 'common.dart';

/// Noi dung dong y su dung du lieu khuon mat (lay tu may chu) + o tick + nut xac nhan.
///
/// - [paper] = false: chinh SV doc va bam dong y trong app (method "self").
/// - [paper] = true: SV da ky ban giay, can bo P.CTSV/admin nhap thay (method "paper") - may
///   chu ghi lai ten can bo da nhap.
/// Gui kem phien ban noi dung dang hien: SV dong y voi dung cai da doc (doi noi dung giua
/// chung thi may chu tra 409 va form tai lai noi dung moi).
class ConsentForm extends StatefulWidget {
  const ConsentForm({super.key, required this.studentId, required this.onDone, this.paper = false, this.notice});

  final int studentId;
  final bool paper;
  final Future<void> Function() onDone;

  /// Dong nhac o dau, vd "Noi dung da cap nhat, vui long xac nhan lai".
  final String? notice;

  @override
  State<ConsentForm> createState() => _ConsentFormState();
}

class _ConsentFormState extends State<ConsentForm> {
  int _reloadKey = 0;
  bool _agree = false;
  bool _busy = false;

  Future<void> _submit(ConsentPolicy policy) async {
    setState(() => _busy = true);
    final api = context.read<ApiClient>();
    try {
      await api.post('/students/${widget.studentId}/consent', data: {
        'agreed': true,
        'version': policy.version,
        'method': widget.paper ? 'paper' : 'self',
      });
      await widget.onDone();
      if (mounted) showSnack(context, widget.paper ? 'Đã ghi nhận đồng ý theo bản giấy' : 'Đã ghi nhận đồng ý');
    } on ApiException catch (e) {
      if (!mounted) return;
      showSnack(context, e.message, error: true);
      // Noi dung vua doi tren may chu: tai lai de nguoi dung doc ban moi roi tick lai.
      if (e.statusCode == 409) {
        setState(() {
          _agree = false;
          _reloadKey++;
        });
      }
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return AsyncLoader<ConsentPolicy>(
      loadKey: _reloadKey,
      load: () async => ConsentPolicy.fromJson(await api.get('/students/consent-policy') as Json),
      builder: (context, policy, _) => SectionCard(
        title: policy.title,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.notice != null)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(widget.notice!),
              ),
            for (final item in policy.items)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [const Text('•  '), Expanded(child: Text(item))],
                ),
              ),
            Text('Phiên bản nội dung: ${policy.version}',
                style: TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant)),
            const SizedBox(height: 4),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _agree,
              onChanged: (v) => setState(() => _agree = v ?? false),
              title: Text(widget.paper
                  ? 'Sinh viên đã ký bản giấy đồng ý với đúng các nội dung trên; tôi nhập thay và chịu trách nhiệm lưu bản giấy.'
                  : policy.checkbox),
            ),
            const SizedBox(height: 4),
            FilledButton(
              onPressed: _agree && !_busy ? () => _submit(policy) : null,
              child: Text(widget.paper ? 'Ghi nhận đồng ý (bản giấy)' : 'Đồng ý và tiếp tục'),
            ),
          ],
        ),
      ),
    );
  }
}
