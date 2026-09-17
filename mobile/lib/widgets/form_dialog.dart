import 'package:flutter/material.dart';

enum FieldKind { text, email, password, number, dropdown, time }

class FieldSpec {
  const FieldSpec(
    this.key,
    this.label, {
    this.kind = FieldKind.text,
    this.required = true,
    this.options = const [],
    this.helper,
    this.minLength,
  });

  final String key;
  final String label;
  final FieldKind kind;
  final bool required;

  /// Lua chon cho dropdown: (gia tri, nhan hien thi). Gia tri null = "khong chon".
  final List<(Object?, String)> options;
  final String? helper;
  final int? minLength;
}

/// Hop thoai form tao/sua ban ghi. Tra ve map gia tri (kieu: String/int/Object?) hoac null neu huy.
/// time: chuoi "HH:MM:SS".
Future<Map<String, dynamic>?> showFormDialog(
  BuildContext context, {
  required String title,
  required List<FieldSpec> fields,
  Map<String, dynamic> initial = const {},
  String submitLabel = 'Lưu',
}) {
  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (context) => _FormDialog(title: title, fields: fields, initial: initial, submitLabel: submitLabel),
  );
}

class _FormDialog extends StatefulWidget {
  const _FormDialog({required this.title, required this.fields, required this.initial, required this.submitLabel});

  final String title;
  final List<FieldSpec> fields;
  final Map<String, dynamic> initial;
  final String submitLabel;

  @override
  State<_FormDialog> createState() => _FormDialogState();
}

class _FormDialogState extends State<_FormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final Map<String, TextEditingController> _text = {
    for (final f in widget.fields)
      if (f.kind != FieldKind.dropdown) f.key: TextEditingController(text: widget.initial[f.key]?.toString() ?? ''),
  };
  late final Map<String, Object?> _dropdown = {
    for (final f in widget.fields)
      if (f.kind == FieldKind.dropdown) f.key: widget.initial[f.key],
  };

  @override
  void dispose() {
    for (final c in _text.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickTime(FieldSpec field) async {
    final current = _text[field.key]!.text;
    final parts = current.split(':');
    final initial = parts.length >= 2
        ? TimeOfDay(hour: int.tryParse(parts[0]) ?? 7, minute: int.tryParse(parts[1]) ?? 0)
        : const TimeOfDay(hour: 7, minute: 0);
    final picked = await showTimePicker(context: context, initialTime: initial);
    if (picked != null) {
      _text[field.key]!.text = '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}:00';
    }
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final result = <String, dynamic>{};
    for (final f in widget.fields) {
      switch (f.kind) {
        case FieldKind.dropdown:
          result[f.key] = _dropdown[f.key];
        case FieldKind.number:
          result[f.key] = int.tryParse(_text[f.key]!.text.trim()) ?? 0;
        default:
          result[f.key] = _text[f.key]!.text.trim();
      }
    }
    Navigator.pop(context, result);
  }

  Widget _field(FieldSpec f) {
    if (f.kind == FieldKind.dropdown) {
      final hasValue = f.options.any((o) => o.$1 == _dropdown[f.key]);
      return DropdownButtonFormField<Object?>(
        initialValue: hasValue ? _dropdown[f.key] : null,
        isExpanded: true,
        decoration: InputDecoration(labelText: f.label, helperText: f.helper),
        items: [for (final (value, label) in f.options) DropdownMenuItem(value: value, child: Text(label, overflow: TextOverflow.ellipsis))],
        onChanged: (v) => setState(() => _dropdown[f.key] = v),
        validator: (v) => f.required && v == null ? 'Bắt buộc chọn' : null,
      );
    }
    return TextFormField(
      controller: _text[f.key],
      readOnly: f.kind == FieldKind.time,
      onTap: f.kind == FieldKind.time ? () => _pickTime(f) : null,
      obscureText: f.kind == FieldKind.password,
      keyboardType: switch (f.kind) {
        FieldKind.email => TextInputType.emailAddress,
        FieldKind.number => TextInputType.number,
        _ => TextInputType.text,
      },
      decoration: InputDecoration(
        labelText: f.label,
        helperText: f.helper,
        suffixIcon: f.kind == FieldKind.time ? const Icon(Icons.schedule) : null,
      ),
      validator: (value) {
        final v = (value ?? '').trim();
        if (f.required && v.isEmpty) return 'Bắt buộc nhập';
        if (v.isEmpty) return null;
        if (f.kind == FieldKind.email && !v.contains('@')) return 'Email không hợp lệ';
        if (f.kind == FieldKind.number && int.tryParse(v) == null) return 'Phải là số';
        if (f.minLength != null && v.length < f.minLength!) return 'Tối thiểu ${f.minLength} ký tự';
        return null;
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: 460,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final f in widget.fields) Padding(padding: const EdgeInsets.only(bottom: 12), child: _field(f)),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Hủy')),
        FilledButton(onPressed: _submit, child: Text(widget.submitLabel)),
      ],
    );
  }
}
