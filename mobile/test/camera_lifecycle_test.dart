import 'package:fams_app/widgets/camera_capture.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// CameraHandle gia: chi dem so lan duoc yeu cau dong/mo lai, khong dung camera that
/// (may chay test khong co camera).
class _FakeCamera extends CameraHandle {
  int suspends = 0;
  int resumes = 0;

  @override
  Future<void> suspend() async => suspends++;

  @override
  Future<void> resume() async => resumes++;
}

class _CameraScreen extends StatefulWidget {
  const _CameraScreen();

  @override
  State<_CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<_CameraScreen> with WidgetsBindingObserver, CameraLifecycleMixin {
  final fake = _FakeCamera();
  int resumedHooks = 0;

  @override
  CameraHandle get camera => fake;

  @override
  void onCameraResumed() => resumedHooks++;

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

void main() {
  testWidgets('tra camera lai cho he dieu hanh khi app chay nen, mo lai khi quay lai', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: _CameraScreen()));
    final state = tester.state<_CameraScreenState>(find.byType(_CameraScreen));
    expect(state.fake.suspends, 0);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();
    expect(state.fake.suspends, 1, reason: 'chuyen sang app khac thi phai nha camera');

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(state.fake.resumes, 1, reason: 'quay lai man hinh thi phai mo lai camera');
    expect(state.resumedHooks, 1, reason: 'man hinh phai duoc bao de chay tiep viec dang do');
  });

  testWidgets('thoi theo doi vong doi sau khi roi man hinh', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: _CameraScreen()));
    final state = tester.state<_CameraScreenState>(find.byType(_CameraScreen));

    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();

    expect(state.fake.suspends, 0, reason: 'man hinh da dong thi khong con nhan su kien vong doi');
  });
}
