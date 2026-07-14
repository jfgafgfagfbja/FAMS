# Model anti-spoofing

Dat file `2.7_80x80_MiniFASNetV2.onnx` vao thu muc nay (`backend/models/`).

## Tai model o dau

1. Repo goc (PyTorch): https://github.com/minivision-ai/Silent-Face-Anti-Spoofing
   File: `resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth`
2. Convert sang ONNX bang `torch.onnx.export` voi input shape `(1, 3, 80, 80)`:
   ```python
   import torch
   from src.model_lib.MiniFASNet import MiniFASNetV2

   model = MiniFASNetV2(conv6_kernel=(5, 5))
   model.load_state_dict(torch.load("2.7_80x80_MiniFASNetV2.pth", map_location="cpu"))
   model.eval()
   dummy = torch.randn(1, 3, 80, 80)
   torch.onnx.export(model, dummy, "2.7_80x80_MiniFASNetV2.onnx",
                      input_names=["input"], output_names=["output"])
   ```
3. Hoac tim ban ONNX da convert san (tim tu khoa "MiniFASNetV2 onnx" / "silent face
   anti spoofing onnx" tren GitHub/Hugging Face) — kiem tra ky nguon truoc khi dung.

## Neu chua co model

Backend van chay binh thuong — `antispoof_service.check_liveness()` se log 1 dong
warning luc goi lan dau va luon tra ve "mat that" (bo qua kiem tra), khong chan
luong nhan dien/dang ky khuon mat.

Muon tat han kiem tra anti-spoofing (vd may dev yeu): dat `ANTISPOOF_ENABLED=False`
trong `.env`.
