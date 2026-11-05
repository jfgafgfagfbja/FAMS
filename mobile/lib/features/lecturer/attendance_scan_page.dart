import 'dart:async';
import 'dart:ui' as ui;

import 'package:camera/camera.dart' show ResolutionPreset;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/camera_capture.dart';
import '../../widgets/common.dart';

const _intervals = [1, 2, 3, 5];

/// Man hinh GV quet camera ca lop: chup dinh ky -> nhan dien -> ve khung mat + cap nhat
/// danh sach lop realtime; xac nhan tay SV khong nhan dien duoc; dong phien.
class AttendanceScanPage extends StatefulWidget {
  const AttendanceScanPage({super.key, required this.sessionId});

  final int sessionId;

  @override
  State<AttendanceScanPage> createState() => _AttendanceScanPageState();
}

class _AttendanceScanPageState extends State<AttendanceScanPage>
    with WidgetsBindingObserver, CameraLifecycleMixin {
  final _camera = CameraHandle();

  @override
  CameraHandle get camera => _camera;
  SessionDetail? _session;
  List<RosterEntry> _roster = const [];
  String? _loadError;

  Timer? _timer;
  bool _sending = false;
  bool _paused = false;
  int _intervalSeconds = 2;
  String? _netError;

  List<RecognizeResult> _results = const [];
  Size? _frameSize;
  bool _flipOverlay = false;
  final Set<int> _spoofIds = {};
  final List<String> _recent = [];
  int? _manualPending;
  bool _closing = false;

  ApiClient get _api => context.read<ApiClient>();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _camera.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        _api.get('/sessions/${widget.sessionId}'),
        _api.get('/sessions/${widget.sessionId}/roster'),
      ]);
      final session = SessionDetail.fromJson(results[0] as Json);
      setState(() {
        _session = session;
        _roster = (results[1] as List<dynamic>).map((e) => RosterEntry.fromJson(e as Json)).toList();
      });
      if (session.isOpen) {
        // Camera lop hoc: mac dinh camera sau (dien thoai/tablet huong ve lop), web dung webcam.
        await _camera.start(preferFront: kIsWeb, preset: ResolutionPreset.high);
        _flipOverlay = _camera.isFront && !kIsWeb;
        if (mounted) setState(() {});
        _restartTimer();
      }
    } catch (e) {
      setState(() => _loadError = errorText(e));
    }
  }

  /// Bat/tat yeu cau quet ma QR cho buoi dang dien ra. Bat xong mo luon man chieu ma.
  Future<void> _toggleQr(bool value) async {
    try {
      final data = await _api.patch('/sessions/${widget.sessionId}',
          data: {'require_qr': value}) as Json;
      if (!mounted) return;
      setState(() => _session = SessionDetail.fromJson(data));
      if (value) context.push('/sessions/${widget.sessionId}/qr');
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    }
  }

  Future<void> _reloadRoster() async {
    final data = await _api.get('/sessions/${widget.sessionId}/roster') as List<dynamic>;
    if (mounted) setState(() => _roster = data.map((e) => RosterEntry.fromJson(e as Json)).toList());
  }

  /// Dang chieu ma thi dung quet: man hinh nay van song phia sau, webcam may giang vien se tu
  /// ghi diem danh cho ai ngoi truoc may trong luc sinh vien dang tu quet ma.
  Future<void> _showQr() async {
    final wasPaused = _paused;
    setState(() => _paused = true);
    await context.push('/sessions/${widget.sessionId}/qr');
    if (mounted) setState(() => _paused = wasPaused);
  }

  void _restartTimer() {
    _timer?.cancel();
    if (_session?.isOpen != true) return;
    _timer = Timer.periodic(Duration(seconds: _intervalSeconds), (_) => _tick());
  }

  Future<void> _tick() async {
    if (_sending || _paused || !_camera.isReady || !mounted) return;
    _sending = true;
    try {
      final bytes = await _camera.capture();
      final size = await _decodeSize(bytes);
      final data = await _api.postMultipart(
        '/sessions/${widget.sessionId}/recognize',
        files: [UploadFile('frame', bytes, 'frame.jpg')],
      ) as List<dynamic>;
      final results = data.map((e) => RecognizeResult.fromJson(e as Json)).toList();
      if (!mounted) return;
      setState(() {
        _results = results;
        _frameSize = size;
        _netError = null;
        _spoofIds.addAll(results.where((r) => r.status == 'spoof' && r.studentId != null).map((r) => r.studentId!));
        for (final r in results.where((r) => r.status == 'recognized')) {
          _recent.insert(0, '✓ ${r.fullName} (${r.confidence.toStringAsFixed(2)}) lúc ${fmtTime(DateTime.now())}');
        }
        if (_recent.length > 8) _recent.removeRange(8, _recent.length);
      });
      if (results.any((r) => r.status == 'recognized')) await _reloadRoster();
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 400 || e.statusCode == 404) {
        // Het han nhan diem danh / phien da dong o noi khac.
        _timer?.cancel();
        setState(() => _netError = e.message);
      } else {
        setState(() => _netError = '${e.message} — sẽ thử lại ở lần chụp sau');
      }
    } catch (e) {
      if (mounted) setState(() => _netError = 'Lỗi chụp/gửi ảnh: $e');
    } finally {
      _sending = false;
    }
  }

  Future<Size> _decodeSize(Uint8List bytes) async {
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final size = Size(frame.image.width.toDouble(), frame.image.height.toDouble());
    frame.image.dispose();
    codec.dispose();
    return size;
  }

  Future<void> _manual(RosterEntry entry) async {
    setState(() => _manualPending = entry.studentId);
    final ok = await runAction(context, () => _api.post('/sessions/${widget.sessionId}/manual', data: {'student_id': entry.studentId}),
        success: 'Đã xác nhận tay ${entry.fullName}');
    if (ok) await _reloadRoster();
    if (mounted) setState(() => _manualPending = null);
  }

  Future<void> _close() async {
    final ok = await confirmDialog(context,
        title: 'Đóng phiên điểm danh?', message: 'Sinh viên chưa điểm danh sẽ được ghi nhận vắng.', confirmLabel: 'Đóng phiên');
    if (!ok || !mounted) return;
    setState(() => _closing = true);
    try {
      final summary = CloseSummary.fromJson(await _api.patch('/sessions/${widget.sessionId}/close') as Json);
      _timer?.cancel();
      await _camera.dispose();
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Đã đóng phiên điểm danh'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Có mặt: ${summary.present}'),
              Text('Vắng: ${summary.absent}'),
              Text('SV vừa vượt ngưỡng vắng: ${summary.newlyWarned.length}'),
              if (summary.newlyWarned.isNotEmpty) Text(summary.newlyWarned.map((w) => w.fullName).join(', ')),
            ],
          ),
          actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Xem chi tiết'))],
        ),
      );
      if (mounted) context.pushReplacement('/sessions/${widget.sessionId}');
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _closing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loadError != null) return ErrorView(message: _loadError!, onRetry: _load);
    final session = _session;
    if (session == null) return const Center(child: CircularProgressIndicator());
    if (!session.isOpen) {
      return EmptyView(
        icon: Icons.task_alt,
        message: 'Phiên điểm danh đã đóng.',
        action: FilledButton(onPressed: () => context.pushReplacement('/sessions/${session.id}'), child: const Text('Xem kết quả')),
      );
    }

    final wide = MediaQuery.sizeOf(context).width >= 1000;
    final header = Wrap(
      spacing: 12,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Text('${session.classCode} — ${session.subjectName}', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
        InfoLine(icon: Icons.schedule, text: '${fmtDate(session.sessionDate)} · ${hhmm(session.startTime)}–${hhmm(session.endTime)} · ${roomLabel(session.room)}'),
        if (session.checkinDeadline != null) InfoLine(icon: Icons.timer_outlined, text: 'Nhận điểm danh tới ${fmtDateTime(session.checkinDeadline)}'),
        // Ma QR xac nhan SV co mat dung phong - GPS chi biet SV o trong khu vuc.
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Switch(value: session.requireQr, onChanged: _toggleQr),
            const Text('Yêu cầu quét mã QR'),
          ],
        ),
        if (session.requireQr)
          OutlinedButton.icon(
            onPressed: _showQr,
            icon: const Icon(Icons.qr_code_2),
            label: const Text('Chiếu mã QR'),
          ),
        FilledButton.icon(
          onPressed: _closing ? null : _close,
          style: FilledButton.styleFrom(backgroundColor: AppColors.brand),
          icon: const Icon(Icons.stop_circle_outlined),
          label: Text(_closing ? 'Đang đóng…' : 'Đóng phiên'),
        ),
      ],
    );

    final cameraPanel = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        CameraPreviewBox(
          handle: _camera,
          showFaceGuide: false,
          overlay: _frameSize == null
              ? null
              : CustomPaint(painter: _FacePainter(results: _results, frameSize: _frameSize!, flip: _flipOverlay)),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            DropdownButton<int>(
              value: _intervalSeconds,
              items: [for (final s in _intervals) DropdownMenuItem(value: s, child: Text('Chụp mỗi $s giây'))],
              onChanged: (v) {
                setState(() => _intervalSeconds = v ?? 2);
                _restartTimer();
              },
            ),
            IconButton.filledTonal(
              tooltip: _paused ? 'Tiếp tục quét' : 'Tạm dừng quét',
              onPressed: () => setState(() => _paused = !_paused),
              icon: Icon(_paused ? Icons.play_arrow : Icons.pause),
            ),
            if (_camera.cameras.length > 1)
              IconButton.filledTonal(
                tooltip: 'Đổi camera',
                onPressed: () async {
                  await _camera.switchCamera();
                  if (mounted) {
                    setState(() {
                      _flipOverlay = _camera.isFront && !kIsWeb;
                      _results = const [];
                    });
                  }
                },
                icon: const Icon(Icons.cameraswitch_outlined),
              ),
            FilterChip(
              label: const Text('Lật khung'),
              selected: _flipOverlay,
              onSelected: (v) => setState(() => _flipOverlay = v),
            ),
          ],
        ),
        if (_netError != null)
          Padding(padding: const EdgeInsets.only(top: 8), child: Text(_netError!, style: const TextStyle(color: AppColors.warning))),
        if (_results.isNotEmpty) ...[
          const SizedBox(height: 8),
          for (final r in _results) _ResultLine(result: r),
        ],
        if (_recent.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text('Vừa nhận diện', style: Theme.of(context).textTheme.labelLarge),
          for (final line in _recent) Text(line, style: const TextStyle(fontSize: 12.5)),
        ],
      ],
    );

    final rosterPanel = _RosterPanel(
      roster: _roster,
      spoofIds: _spoofIds,
      manualPending: _manualPending,
      onManual: _manual,
    );

    return PageBody(
      maxWidth: 1400,
      onRefresh: _reloadRoster,
      children: [
        header,
        const SizedBox(height: 16),
        if (wide)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 3, child: cameraPanel),
              const SizedBox(width: 16),
              Expanded(flex: 2, child: rosterPanel),
            ],
          )
        else ...[
          cameraPanel,
          const SizedBox(height: 16),
          rosterPanel,
        ],
      ],
    );
  }
}

class _ResultLine extends StatelessWidget {
  const _ResultLine({required this.result});

  final RecognizeResult result;

  @override
  Widget build(BuildContext context) {
    final text = switch (result.status) {
      'spoof' => '⚠ Nghi giả mạo${result.fullName != null ? ' — ${result.studentCode} ${result.fullName}' : ''}',
      'unknown' => 'Không nhận diện được (độ khớp ${result.confidence.toStringAsFixed(2)})',
      'confirming' => '${result.fullName} — đang xác nhận (${result.confirmCount}/${result.confirmNeeded})',
      'already_checked' => '${result.studentCode} ${result.fullName} — đã điểm danh',
      _ => '${result.studentCode} ${result.fullName} — ghi nhận (${result.confidence.toStringAsFixed(2)})',
    };
    return Text(text, style: TextStyle(color: statusColor(result.status), fontSize: 13));
  }
}

class _RosterPanel extends StatelessWidget {
  const _RosterPanel({required this.roster, required this.spoofIds, required this.manualPending, required this.onManual});

  final List<RosterEntry> roster;
  final Set<int> spoofIds;
  final int? manualPending;
  final ValueChanged<RosterEntry> onManual;

  @override
  Widget build(BuildContext context) {
    final present = roster.where((r) => r.status == 'present' || r.status == 'manual').length;
    final late = roster.where((r) => r.status == 'late').length;
    final unchecked = roster.where((r) => r.status == null).length;
    return SectionCard(
      title: 'Danh sách lớp',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              StatusChip(label: 'Có mặt $present/${roster.length}', color: AppColors.success),
              StatusChip(label: 'Muộn $late', color: AppColors.warning),
              StatusChip(label: 'Chưa $unchecked', color: AppColors.neutral),
            ],
          ),
          const SizedBox(height: 8),
          if (roster.isEmpty)
            const Text('Lớp chưa có sinh viên ghi danh.')
          else
            for (final entry in roster)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text(entry.fullName),
                subtitle: Text(entry.studentCode),
                trailing: entry.status != null
                    ? StatusChip.attendance(entry.status)
                    : spoofIds.contains(entry.studentId)
                        ? const StatusChip(label: 'Nghi gian lận', color: AppColors.danger, icon: Icons.warning_amber_rounded)
                        : OutlinedButton(
                            onPressed: manualPending == entry.studentId ? null : () => onManual(entry),
                            child: Text(manualPending == entry.studentId ? 'Đang xác nhận…' : 'Xác nhận tay'),
                          ),
              ),
        ],
      ),
    );
  }
}

/// Ve khung mat len preview. bbox tinh theo pixel anh da gui len (frameSize); preview
/// hien thi cung ti le nen chi can scale. flip: camera truoc tren mobile hien preview
/// dang guong trong khi anh chup thi khong.
class _FacePainter extends CustomPainter {
  _FacePainter({required this.results, required this.frameSize, required this.flip});

  final List<RecognizeResult> results;
  final Size frameSize;
  final bool flip;

  @override
  void paint(Canvas canvas, Size size) {
    final sx = size.width / frameSize.width;
    final sy = size.height / frameSize.height;
    for (final r in results) {
      final bbox = r.bbox;
      if (bbox == null || bbox.length != 4) continue;
      var left = bbox[0] * sx;
      var right = bbox[2] * sx;
      if (flip) {
        final l = size.width - right;
        right = size.width - left;
        left = l;
      }
      final rect = Rect.fromLTRB(left, bbox[1] * sy, right, bbox[3] * sy);
      final color = statusColor(r.status);
      canvas.drawRect(rect, Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3);

      final label = r.status == 'spoof'
          ? '⚠ giả mạo'
          : r.fullName != null
              ? '${r.fullName} (${r.confidence.toStringAsFixed(2)})'
              : '? (${r.confidence.toStringAsFixed(2)})';
      final painter = TextPainter(
        text: TextSpan(text: label, style: const TextStyle(color: Colors.black, fontSize: 13, fontWeight: FontWeight.w600)),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: 260);
      final top = (rect.top - painter.height - 4).clamp(0.0, size.height);
      canvas.drawRect(Rect.fromLTWH(rect.left, top, painter.width + 8, painter.height + 4), Paint()..color = color);
      painter.paint(canvas, Offset(rect.left + 4, top + 2));
    }
  }

  @override
  bool shouldRepaint(covariant _FacePainter oldDelegate) =>
      oldDelegate.results != results || oldDelegate.frameSize != frameSize || oldDelegate.flip != flip;
}
