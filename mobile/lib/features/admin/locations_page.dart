import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Dia diem diem danh (co so/toa nha) + ban kinh cho phep khi SV tu diem danh bang GPS.
/// Quan ly boi admin va Phong Dao tao.
class LocationsPage extends StatelessWidget {
  const LocationsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return AsyncLoader<List<Location>>(
      load: () async => (await api.get('/locations') as List<dynamic>).map((e) => Location.fromJson(e as Json)).toList(),
      builder: (context, locations, reload) => PageBody(
        maxWidth: 900,
        onRefresh: reload,
        children: [
          const Text(
            'Sinh viên chỉ tự điểm danh (selfie) được khi vị trí GPS nằm trong bán kính của địa điểm gắn với lịch học. '
            'Lịch học chưa gắn địa điểm sẽ dùng địa điểm mặc định. Chưa có địa điểm nào thì không đối chiếu vị trí.',
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: () async {
                if (await showLocationDialog(context)) reload();
              },
              icon: const Icon(Icons.add_location_alt_outlined),
              label: const Text('Thêm địa điểm'),
            ),
          ),
          const SizedBox(height: 12),
          if (locations.isEmpty)
            const EmptyView(icon: Icons.location_off_outlined, message: 'Chưa có địa điểm điểm danh — hiện không đối chiếu GPS.')
          else
            Card(
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
                  for (final location in locations)
                    ListTile(
                      leading: Icon(Icons.place, color: location.isDefault ? AppColors.brand : null),
                      title: Row(
                        children: [
                          Flexible(child: Text(location.name)),
                          if (location.isDefault) ...[
                            const SizedBox(width: 8),
                            const StatusChip(label: 'Mặc định', color: AppColors.brand),
                          ],
                        ],
                      ),
                      subtitle: Text(
                        '${location.code} · ${location.latitude.toStringAsFixed(5)}, ${location.longitude.toStringAsFixed(5)} · '
                        'bán kính ${location.radiusM.round()} m',
                      ),
                      trailing: Wrap(
                        children: [
                          IconButton(
                            tooltip: 'Xem trên bản đồ',
                            onPressed: () => openMap(location.latitude, location.longitude),
                            icon: const Icon(Icons.map_outlined),
                          ),
                          IconButton(
                            tooltip: 'Sửa',
                            onPressed: () async {
                              if (await showLocationDialog(context, location: location)) reload();
                            },
                            icon: const Icon(Icons.edit_outlined),
                          ),
                          IconButton(
                            tooltip: 'Xóa',
                            onPressed: () async {
                              final ok = await confirmDialog(context,
                                  title: 'Xóa địa điểm?',
                                  message: 'Chỉ xóa được khi không còn lịch học nào gắn với địa điểm này.',
                                  confirmLabel: 'Xóa',
                                  destructive: true);
                              if (ok && context.mounted &&
                                  await runAction(context, () => api.delete('/locations/${location.id}'), success: 'Đã xóa')) {
                                reload();
                              }
                            },
                            icon: const Icon(Icons.delete_outline),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

Future<bool> showLocationDialog(BuildContext context, {Location? location}) async {
  final saved = await showDialog<bool>(
    context: context,
    builder: (context) => _LocationDialog(location: location),
  );
  return saved ?? false;
}

class _LocationDialog extends StatefulWidget {
  const _LocationDialog({this.location});

  final Location? location;

  @override
  State<_LocationDialog> createState() => _LocationDialogState();
}

class _LocationDialogState extends State<_LocationDialog> {
  final _formKey = GlobalKey<FormState>();
  late final _code = TextEditingController(text: widget.location?.code);
  late final _name = TextEditingController(text: widget.location?.name);
  late final _lat = TextEditingController(text: widget.location?.latitude.toString());
  late final _lng = TextEditingController(text: widget.location?.longitude.toString());
  late final _radius = TextEditingController(text: (widget.location?.radiusM ?? 150).round().toString());
  late bool _isDefault = widget.location?.isDefault ?? false;
  bool _locating = false;
  bool _saving = false;

  @override
  void dispose() {
    for (final c in [_code, _name, _lat, _lng, _radius]) {
      c.dispose();
    }
    super.dispose();
  }

  /// Can bo dung tai co so bam nut nay de lay toa do chinh xac thay vi nhap tay.
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

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    final api = context.read<ApiClient>();
    final data = {
      'code': _code.text.trim(),
      'name': _name.text.trim(),
      'latitude': double.parse(_lat.text.trim()),
      'longitude': double.parse(_lng.text.trim()),
      'radius_m': double.parse(_radius.text.trim()),
      'is_default': _isDefault,
    };
    final location = widget.location;
    final ok = await runAction(
      context,
      () => location == null ? api.post('/locations', data: data) : api.patch('/locations/${location.id}', data: data),
      success: location == null ? 'Đã thêm địa điểm' : 'Đã cập nhật địa điểm',
    );
    if (!mounted) return;
    setState(() => _saving = false);
    if (ok) Navigator.pop(context, true);
  }

  String? _number(String? value, {required double min, required double max}) {
    final v = double.tryParse((value ?? '').trim());
    if (v == null) return 'Nhập số';
    if (v < min || v > max) return 'Từ $min đến $max';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.location == null ? 'Thêm địa điểm điểm danh' : 'Sửa địa điểm điểm danh'),
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
                  decoration: const InputDecoration(labelText: 'Mã địa điểm', helperText: 'VD: CS-NUITHANH'),
                  validator: (v) => (v ?? '').trim().isEmpty ? 'Bắt buộc nhập' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Tên địa điểm'),
                  validator: (v) => (v ?? '').trim().isEmpty ? 'Bắt buộc nhập' : null,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _lat,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Vĩ độ'),
                        validator: (v) => _number(v, min: -90, max: 90),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _lng,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Kinh độ'),
                        validator: (v) => _number(v, min: -180, max: 180),
                      ),
                    ),
                  ],
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: _locating ? null : _useCurrentPosition,
                    icon: const Icon(Icons.my_location),
                    label: Text(_locating ? 'Đang lấy vị trí…' : 'Lấy vị trí hiện tại (đứng tại cơ sở)'),
                  ),
                ),
                TextFormField(
                  controller: _radius,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Bán kính cho phép (m)',
                    helperText: 'GPS trong nhà sai số vài chục mét — nên đặt 100–300 m cho cả khuôn viên',
                  ),
                  validator: (v) => _number(v, min: 10, max: 5000),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _isDefault,
                  onChanged: (v) => setState(() => _isDefault = v),
                  title: const Text('Địa điểm mặc định'),
                  subtitle: const Text('Áp dụng cho lịch học chưa gắn địa điểm riêng'),
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
