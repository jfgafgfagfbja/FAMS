import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/formatters.dart';
import '../models/models.dart';

/// Tai danh sach don vi (co cache trong phien) cho dropdown chon Khoa/don vi.
class UnitCache {
  static List<Unit>? _units;

  static Future<List<Unit>> load(ApiClient api, {bool force = false}) async {
    if (_units != null && !force) return _units!;
    final data = await api.get('/units') as List<dynamic>;
    return _units = data.map((e) => Unit.fromJson(e as Json)).toList();
  }

  static void invalidate() => _units = null;
}

class UnitDropdown extends StatefulWidget {
  const UnitDropdown({
    super.key,
    required this.value,
    required this.onChanged,
    this.facultiesOnly = true,
    this.label = 'Khoa',
    this.allowEmpty = true,
    this.emptyLabel = 'Tất cả',
    this.width = 240,
  });

  final int? value;
  final ValueChanged<int?> onChanged;
  final bool facultiesOnly;
  final String label;
  final bool allowEmpty;
  final String emptyLabel;
  final double width;

  @override
  State<UnitDropdown> createState() => _UnitDropdownState();
}

class _UnitDropdownState extends State<UnitDropdown> {
  List<Unit> _units = const [];

  @override
  void initState() {
    super.initState();
    UnitCache.load(context.read<ApiClient>()).then((units) {
      if (mounted) setState(() => _units = units);
    }).catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    final units = widget.facultiesOnly ? _units.where((u) => u.type == 'faculty').toList() : _units;
    final hasValue = units.any((u) => u.id == widget.value);
    return SizedBox(
      width: widget.width,
      child: DropdownButtonFormField<int?>(
        key: ValueKey('${widget.value}-${units.length}'),
        initialValue: hasValue ? widget.value : null,
        isExpanded: true,
        decoration: InputDecoration(labelText: widget.label),
        items: [
          if (widget.allowEmpty) DropdownMenuItem<int?>(value: null, child: Text(widget.emptyLabel)),
          for (final u in units)
            DropdownMenuItem<int?>(
              value: u.id,
              child: Text(widget.facultiesOnly ? u.name : '${u.name} (${unitTypeLabel(u.type)})', overflow: TextOverflow.ellipsis),
            ),
        ],
        onChanged: widget.onChanged,
      ),
    );
  }
}

class SemesterDropdown extends StatelessWidget {
  const SemesterDropdown({
    super.key,
    required this.value,
    required this.options,
    required this.onChanged,
    this.allowLatest = true,
    this.width = 220,
  });

  final String? value;
  final List<String> options;
  final ValueChanged<String?> onChanged;
  final bool allowLatest;
  final double width;

  @override
  Widget build(BuildContext context) {
    final all = {...options, ?value}.toList()..sort((a, b) => b.compareTo(a));
    return SizedBox(
      width: width,
      child: DropdownButtonFormField<String?>(
        key: ValueKey('$value-${all.length}'),
        initialValue: value,
        isExpanded: true,
        decoration: const InputDecoration(labelText: 'Học kỳ'),
        items: [
          if (allowLatest) const DropdownMenuItem<String?>(value: null, child: Text('Mới nhất')),
          for (final s in all) DropdownMenuItem<String?>(value: s, child: Text(formatSemester(s))),
        ],
        onChanged: onChanged,
      ),
    );
  }
}
