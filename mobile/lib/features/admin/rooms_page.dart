import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Danh muc phong hoc: nguon chon phong khi xep lich, va lop trong cung cua viec
/// doi chieu vi tri (phong -> khu vuc chua phong). Quan ly boi admin va Phong Dao tao.
class RoomsPage extends StatefulWidget {
  const RoomsPage({super.key});

  @override
  State<RoomsPage> createState() => _RoomsPageState();
}

class _RoomsPageState extends State<RoomsPage> {
  String? _building;
  bool _showInactive = false;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return AsyncLoader<(List<Room>, List<Location>)>(
      loadKey: '$_building/$_showInactive',
      load: () async {
        final query = <String, dynamic>{'only_active': !_showInactive};
        if (_building != null) query['building'] = _building;
        final results = await Future.wait([
          api.get('/rooms', query: query),
          api.get('/locations'),
        ]);
        return (
          (results[0] as List<dynamic>).map((e) => Room.fromJson(e as Json)).toList(),
          (results[1] as List<dynamic>).map((e) => Location.fromJson(e as Json)).toList(),
        );
      },
      builder: (context, data, reload) {
        final (rooms, locations) = data;
        final buildings = {for (final r in rooms) if (r.building?.isNotEmpty ?? false) r.building!}.toList()..sort();
        return PageBody(
          maxWidth: 900,
          onRefresh: reload,
          children: [
            const Text(
              'Phòng học dùng để xếp lịch và để biết buổi học diễn ra ở đâu. Khi sinh viên tự điểm danh, '
              'hệ thống đối chiếu vị trí theo tọa độ riêng của phòng nếu có, nếu không thì theo khu vực chứa phòng.',
            ),
            const SizedBox(height: 4),
            Text(
              'GPS điện thoại sai số vài chục mét nên không phân biệt được hai phòng cạnh nhau — '
              'bán kính luôn được nâng lên tối thiểu 50 m dù nhập nhỏ hơn.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.neutral),
            ),
            const SizedBox(height: 12),
            if (locations.isEmpty)
              const EmptyView(
                icon: Icons.location_off_outlined,
                message: 'Chưa có khu vực nào. Hãy thêm địa điểm (cơ sở/tòa nhà) trước, rồi mới thêm phòng vào đó.',
              )
            else ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  FilledButton.icon(
                    onPressed: () async {
                      if (await showRoomDialog(context, locations: locations)) reload();
                    },
                    icon: const Icon(Icons.meeting_room_outlined),
                    label: const Text('Thêm phòng'),
                  ),
                  if (buildings.isNotEmpty || _building != null)
                    DropdownButton<String?>(
                      value: _building,
                      hint: const Text('Tất cả tòa nhà'),
                      items: [
                        const DropdownMenuItem(value: null, child: Text('Tất cả tòa nhà')),
                        for (final b in buildings) DropdownMenuItem(value: b, child: Text('Nhà $b')),
                      ],
                      onChanged: (v) => setState(() => _building = v),
                    ),
                  FilterChip(
                    selected: _showInactive,
                    onSelected: (v) => setState(() => _showInactive = v),
                    label: const Text('Hiện cả phòng ngừng dùng'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (rooms.isEmpty)
                const EmptyView(icon: Icons.meeting_room_outlined, message: 'Chưa có phòng học nào.')
              else
                Card(
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    children: [
                      for (final room in rooms)
                        _RoomTile(room: room, locations: locations, reload: reload),
                    ],
                  ),
                ),
            ],
          ],
        );
      },
    );
  }
}

class _RoomTile extends StatelessWidget {
  const _RoomTile({required this.room, required this.locations, required this.reload});

  final Room room;
  final List<Location> locations;
  final Future<void> Function() reload;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final subtitle = [
      room.code,
      if (room.details.isNotEmpty) room.details,
      if (room.hasOwnPoint)
        'tọa độ riêng · bán kính ${room.effectiveRadiusM?.round()} m'
      else
        'theo ${room.locationName ?? 'khu vực'}',
      if (room.scheduleCount > 0) '${room.scheduleCount} lịch học',
    ].join(' · ');

    return ListTile(
      leading: Icon(Icons.meeting_room,
          color: room.isActive ? (room.hasOwnPoint ? AppColors.brand : null) : AppColors.neutral),
      title: Row(
        children: [
          Flexible(child: Text(room.name)),
          if (!room.isActive) ...[
            const SizedBox(width: 8),
            const StatusChip(label: 'Ngừng dùng', color: AppColors.neutral),
          ],
        ],
      ),
      subtitle: Text(subtitle),
      trailing: Wrap(
        children: [
          if (room.hasOwnPoint)
            IconButton(
              tooltip: 'Xem trên bản đồ',
              onPressed: () => openMap(room.latitude!, room.longitude!),
              icon: const Icon(Icons.map_outlined),
            ),
          IconButton(
            tooltip: 'Sửa',
            onPressed: () async {
              if (await showRoomDialog(context, locations: locations, room: room)) reload();
            },
            icon: const Icon(Icons.edit_outlined),
          ),
          IconButton(
            tooltip: 'Xóa',
            onPressed: () async {
              final ok = await confirmDialog(context,
                  title: 'Xóa phòng?',
                  message: room.scheduleCount > 0
                      ? 'Phòng đang có ${room.scheduleCount} lịch học nên không xóa được. '
                          'Hãy đánh dấu ngừng sử dụng để giữ lịch sử.'
                      : 'Chỉ xóa được khi không còn lịch học nào dùng phòng này.',
                  confirmLabel: 'Xóa',
                  destructive: true);
              if (ok && context.mounted &&
                  await runAction(context, () => api.delete('/rooms/${room.id}'), success: 'Đã xóa')) {
                reload();
              }
            },
            icon: const Icon(Icons.delete_outline),
          ),
        ],
      ),
    );
  }
}

Future<bool> showRoomDialog(BuildContext context, {required List<Location> locations, Room? room}) async {
  final saved = await showDialog<bool>(
    context: context,
    builder: (context) => _RoomDialog(locations: locations, room: room),
  );
  return saved ?? false;
}

class _RoomDialog extends StatefulWidget {
  const _RoomDialog({required this.locations, this.room});

  final List<Location> locations;
  final Room? room;

  @override
  State<_RoomDialog> createState() => _RoomDialogState();
}

class _RoomDialogState extends State<_RoomDialog> {
  final _formKey = GlobalKey<FormState>();
  late final _code = TextEditingController(text: widget.room?.code);
  late final _name = TextEditingController(text: widget.room?.name);
  late final _building = TextEditingController(text: widget.room?.building);
  late final _floor = TextEditingController(text: widget.room?.floor?.toString());
  late final _capacity = TextEditingController(text: widget.room?.capacity?.toString());
  late final _lat = TextEditingController(text: widget.room?.latitude?.toString());
  late final _lng = TextEditingController(text: widget.room?.longitude?.toString());
  late final _radius = TextEditingController(text: widget.room?.radiusM?.round().toString());
  late int _locationId = widget.room?.locationId ?? widget.locations.first.id;
  late bool _isActive = widget.room?.isActive ?? true;
  bool _locating = false;
  bool _saving = false;

  @override
  void dispose() {
    for (final c in [_code, _name, _building, _floor, _capacity, _lat, _lng, _radius]) {
      c.dispose();
    }
    super.dispose();
  }

  /// Dung ngay truoc toa nha roi bam nut nay - chinh xac hon nhap tay toa do.
  Future<void> _useCurrentPosition() async {
    setState(() => _locating = true);
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        throw Exception('Chưa cấp quyền vị trí');
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.best, timeLimit: Duration(seconds: 20)),
      );
      _lat.text = position.latitude.toStringAsFixed(6);
      _lng.text = position.longitude.toStringAsFixed(6);
      if (mounted) showSnack(context, 'Đã lấy vị trí (sai số ~${position.accuracy.round()} m)');
    } catch (e) {
      if (mounted) showSnack(context, 'Không lấy được vị trí: $e', error: true);
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  double? _parsed(TextEditingController c) {
    final text = c.text.trim();
    return text.isEmpty ? null : double.tryParse(text);
  }

  int? _parsedInt(TextEditingController c) {
    final text = c.text.trim();
    return text.isEmpty ? null : int.tryParse(text);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    final api = context.read<ApiClient>();
    final data = {
      'code': _code.text.trim(),
      'name': _name.text.trim(),
      'location_id': _locationId,
      'building': _building.text.trim().isEmpty ? null : _building.text.trim(),
      'floor': _parsedInt(_floor),
      'capacity': _parsedInt(_capacity),
      'latitude': _parsed(_lat),
      'longitude': _parsed(_lng),
      'radius_m': _parsed(_radius),
      'is_active': _isActive,
    };
    final room = widget.room;
    final ok = await runAction(
      context,
      () => room == null ? api.post('/rooms', data: data) : api.patch('/rooms/${room.id}', data: data),
      success: room == null ? 'Đã thêm phòng' : 'Đã cập nhật phòng',
    );
    if (!mounted) return;
    setState(() => _saving = false);
    if (ok) Navigator.pop(context, true);
  }

  /// O so khong bat buoc: de trong thi hop le, co nhap thi phai dung khoang.
  String? _optionalNumber(String? value, {required double min, required double max}) {
    final text = (value ?? '').trim();
    if (text.isEmpty) return null;
    final v = double.tryParse(text);
    if (v == null) return 'Nhập số';
    if (v < min || v > max) return 'Từ ${min.round()} đến ${max.round()}';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final hasOnePoint = _lat.text.trim().isNotEmpty || _lng.text.trim().isNotEmpty;
    return AlertDialog(
      title: Text(widget.room == null ? 'Thêm phòng học' : 'Sửa phòng học'),
      content: SizedBox(
        width: 460,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _code,
                  decoration: const InputDecoration(labelText: 'Mã phòng', helperText: 'VD: E2-101'),
                  validator: (v) => (v ?? '').trim().isEmpty ? 'Bắt buộc nhập' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Tên hiển thị', helperText: 'VD: Phòng 101 — Nhà E2'),
                  validator: (v) => (v ?? '').trim().isEmpty ? 'Bắt buộc nhập' : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: _locationId,
                  decoration: const InputDecoration(labelText: 'Thuộc khu vực'),
                  items: [
                    for (final l in widget.locations)
                      DropdownMenuItem(value: l.id, child: Text('${l.name} (${l.radiusM.round()} m)')),
                  ],
                  onChanged: (v) => setState(() => _locationId = v ?? _locationId),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _building,
                        decoration: const InputDecoration(labelText: 'Tòa nhà', helperText: 'VD: E2'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _floor,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Tầng'),
                        validator: (v) => _optionalNumber(v, min: -5, max: 100),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _capacity,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Sức chứa'),
                        validator: (v) => _optionalNumber(v, min: 1, max: 2000),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Tọa độ riêng (không bắt buộc)', style: TextStyle(fontWeight: FontWeight.w600)),
                ),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Để trống thì phòng dùng chung tọa độ của khu vực. Nhập tọa độ giúp đối chiếu sát hơn '
                    'khi trường có nhiều tòa nhà cách xa nhau.',
                    style: TextStyle(fontSize: 12, color: AppColors.neutral),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _lat,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Vĩ độ'),
                        onChanged: (_) => setState(() {}),
                        validator: (v) => _optionalNumber(v, min: -90, max: 90),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _lng,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Kinh độ'),
                        onChanged: (_) => setState(() {}),
                        validator: (v) => _optionalNumber(v, min: -180, max: 180),
                      ),
                    ),
                  ],
                ),
                if (hasOnePoint && (_lat.text.trim().isEmpty || _lng.text.trim().isEmpty))
                  const Padding(
                    padding: EdgeInsets.only(top: 6),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text('Phải nhập cả vĩ độ và kinh độ, hoặc bỏ trống cả hai',
                          style: TextStyle(fontSize: 12, color: AppColors.danger)),
                    ),
                  ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: _locating ? null : _useCurrentPosition,
                    icon: const Icon(Icons.my_location),
                    label: Text(_locating ? 'Đang lấy vị trí…' : 'Lấy vị trí hiện tại (đứng tại tòa nhà)'),
                  ),
                ),
                TextFormField(
                  controller: _radius,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Bán kính riêng (m)',
                    helperText: 'Để trống = 50 m. Nhập nhỏ hơn 50 m vẫn được nâng lên 50 m vì sai số GPS.',
                  ),
                  validator: (v) => _optionalNumber(v, min: 10, max: 5000),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _isActive,
                  onChanged: (v) => setState(() => _isActive = v),
                  title: const Text('Còn sử dụng'),
                  subtitle: const Text('Tắt thì phòng không hiện khi xếp lịch mới, lịch cũ giữ nguyên'),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Hủy')),
        FilledButton(onPressed: _saving ? null : _save, child: const Text('Lưu')),
      ],
    );
  }
}
