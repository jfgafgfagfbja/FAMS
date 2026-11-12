"""Do hieu nang cac buoc nhan dien de dien bang "Ket qua do hieu nang" cua bao cao.

Chay TRONG moi truong co day du thu vien (venv cua backend, hoac container backend),
va co bien DATABASE_URL tro toi Postgres that.

    cd backend
    python tools/do_hieu_nang.py --anh-mot-mat ../anh/mot-mat.jpg \\
                                 --anh-nhieu-mat ../anh/ca-lop.jpg --ghi

Trong Docker:
    docker compose cp backend/tools/do_hieu_nang.py backend:/app/tools/do_hieu_nang.py
    docker compose cp anh/ backend:/app/anh
    docker compose exec backend python tools/do_hieu_nang.py --anh-mot-mat anh/mot-mat.jpg

Anh dau vao phai la anh THAT chup bang camera se dung khi bao ve, vi toc do phu thuoc
do phan giai. Khong co anh nao thi script chi do duoc phep truy van so khop trong CSDL.

--ghi: ghi ../baocao/auto/bang-hieu-nang.tex. Chuong 5 tu dong dung file do neu co,
nguoc lai in cac o "CAN BO SUNG".
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings                      # noqa: E402
from app.db import models                                 # noqa: E402
from app.db.database import SessionLocal                  # noqa: E402
from app.services import antispoof_service, face_service  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
FILE_KET_QUA = GOC / "baocao" / "auto" / "bang-hieu-nang.tex"

# Ten dong trong bang cua bao cao -> khoa noi bo. Giu dung thu tu cua bang.
DONG_BANG = [
    ("mot_mat", "Phát hiện và trích đặc trưng một khuôn mặt"),
    ("nhieu_mat", "Khung hình có năm khuôn mặt"),
    ("truy_van", "Truy vấn so khớp trong cơ sở dữ liệu"),
    ("chong_gia_mao", "Kiểm tra chống giả mạo một khuôn mặt"),
    ("tron_ven", "Thời gian đáp ứng trọn vẹn một yêu cầu nhận diện"),
]


def do(ham, lan: int) -> tuple[float, float] | None:
    """Chay ham nhieu lan, bo lan dau (nap mo hinh), tra ve (trung vi, lon nhat) theo ms."""
    try:
        ham()  # lan khoi dong, khong tinh gio
    except Exception as loi:  # noqa: BLE001 - bao ro roi bo qua phep do nay
        print(f"    bo qua: {loi}")
        return None
    moc = []
    for _ in range(lan):
        t0 = time.perf_counter()
        ham()
        moc.append((time.perf_counter() - t0) * 1000)
    return statistics.median(moc), max(moc)


def doc_anh(duong_dan: str | None) -> bytes | None:
    if not duong_dan:
        return None
    p = Path(duong_dan)
    if not p.exists():
        print(f"[!] Khong thay anh: {p}")
        return None
    return p.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description="Do hieu nang nhan dien cua FAMS")
    parser.add_argument("--anh-mot-mat", help="Anh co dung 1 khuon mat")
    parser.add_argument("--anh-nhieu-mat", help="Anh chup ca lop, nhieu khuon mat")
    parser.add_argument("--lan", type=int, default=30, help="So lan lap moi phep do")
    parser.add_argument("--ghi", action="store_true",
                        help="Ghi ket qua ra baocao/auto/bang-hieu-nang.tex")
    args = parser.parse_args()

    anh_mot = doc_anh(args.anh_mot_mat)
    anh_nhieu = doc_anh(args.anh_nhieu_mat)
    ket_qua: dict[str, tuple[float, float] | None] = {k: None for k, _ in DONG_BANG}
    # Cac so phu de van xuoi trong bao cao dung lai (xem phan --ghi o cuoi).
    phu: dict[str, float | int | None] = {"so_mat": None, "so_vector": None,
                                          "gon_mot": None, "gon_nhieu": None}
    # Nhan dong "nhieu mat" lay theo so khuon mat dem duoc trong anh, khong viet cung.
    nhan_dong = dict(DONG_BANG)

    print(f"Moi phep do lap {args.lan} lan, bo lan dau tien.\n")

    if anh_mot:
        print("[1] Phat hien + trich dac trung, anh 1 khuon mat")
        img = face_service._decode_image(anh_mot)
        ket_qua["mot_mat"] = do(lambda: face_service.get_engine().get(img), args.lan)

        khuon_mat = face_service.get_engine().get(img)
        if khuon_mat:
            print("[4] Kiem tra chong gia mao 1 khuon mat")
            bbox = khuon_mat[0].bbox
            # Thieu tep mo hinh thi check_liveness tra ve ngay, do se ra 0 ms gia.
            if settings.ANTISPOOF_ENABLED and antispoof_service._load_session() is None:
                print("    bo qua: thieu tep mo hinh MiniFASNetV2, chua do duoc")
            elif settings.ANTISPOOF_ENABLED:
                ket_qua["chong_gia_mao"] = do(
                    lambda: antispoof_service.check_liveness(img, bbox), args.lan)
            else:
                print("    bo qua: ANTISPOOF_ENABLED dang tat")
        else:
            print("[!] Khong tim thay khuon mat nao trong anh 1 mat")
    else:
        print("[1][4] bo qua: chua truyen --anh-mot-mat")

    if anh_nhieu:
        print("[2] Phat hien + trich dac trung, anh nhieu khuon mat")
        img_nhieu = face_service._decode_image(anh_nhieu)
        so_mat = len(face_service.get_engine().get(img_nhieu))
        print(f"    anh nay co {so_mat} khuon mat")
        nhan_dong["nhieu_mat"] = f"Khung hình có {so_mat} khuôn mặt"
        phu["so_mat"] = so_mat
        ket_qua["nhieu_mat"] = do(lambda: face_service.get_engine().get(img_nhieu), args.lan)
    else:
        print("[2] bo qua: chua truyen --anh-nhieu-mat")

    # So sanh: he thong nap ca bo buffalo_l (5 mo hinh), trong khi chi dung phat hien va
    # trich dac trung. Do lai cung anh voi cau hinh chi nap hai mo hinh do.
    if anh_mot or anh_nhieu:
        print("[6] So sanh: chi nap phat hien + trich dac trung")
        from insightface.app import FaceAnalysis
        gon = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"],
                           allowed_modules=["detection", "recognition"])
        gon.prepare(ctx_id=0, det_size=(640, 640))
        if anh_mot:
            kq = do(lambda: gon.get(img), args.lan)
            phu["gon_mot"] = kq[0] if kq else None
        if anh_nhieu:
            kq = do(lambda: gon.get(img_nhieu), args.lan)
            phu["gon_nhieu"] = kq[0] if kq else None

    db = SessionLocal()
    try:
        so_vector = db.query(models.FaceEmbedding).count()
        phu["so_vector"] = so_vector
        lop = db.query(models.Class).first()
        print(f"\n[3] Truy van so khop trong CSDL ({so_vector} vector da dang ky)")
        if so_vector == 0:
            print("    bo qua: CSDL chua co vector nao, hay dang ky khuon mat truoc")
        else:
            vector_ngau_nhien = np.random.rand(512).astype(np.float32)
            vector_ngau_nhien /= np.linalg.norm(vector_ngau_nhien)
            dsach = vector_ngau_nhien.tolist()

            def truy_van():
                khoang_cach = models.FaceEmbedding.embedding.cosine_distance(dsach)
                return (db.query(models.FaceEmbedding.student_id, khoang_cach)
                        .filter(models.FaceEmbedding.status == "approved")
                        .order_by(khoang_cach).first())

            ket_qua["truy_van"] = do(truy_van, args.lan)

        if anh_mot and lop is not None:
            print(f"[5] Nhan dien tron ven mot khung hinh (lop id={lop.id})")
            ket_qua["tron_ven"] = do(
                lambda: face_service.recognize_frame(db, anh_mot, lop.id), args.lan)
        elif lop is None:
            print("[5] bo qua: CSDL chua co lop hoc phan nao (chay seed.py truoc)")
    finally:
        db.close()

    print("\n" + "=" * 62)
    print(f"{'Phep do':<52}{'Trung vi':>10}{'Lon nhat':>10}")
    for khoa, nhan in nhan_dong.items():
        gt = ket_qua[khoa]
        if gt:
            print(f"{nhan:<52}{gt[0]:>9.1f}{gt[1]:>10.1f}")
        else:
            print(f"{nhan:<52}{'--':>10}{'--':>10}")

    if args.ghi:
        # Boc thanh lenh chu khong de dong tho: bao cao nap file nay o preamble roi goi
        # \BangHieuNang trong than bang, vi tabularx khong chiu duoc \input ben trong.
        dong = ["% File nay do backend/tools/do_hieu_nang.py sinh ra. KHONG SUA TAY.",
                f"% Do luc {time.strftime('%d/%m/%Y %H:%M')}, lap {args.lan} lan moi phep do.",
                "\\renewcommand{\\BangHieuNang}{%"]
        for khoa, nhan in nhan_dong.items():
            gt = ket_qua[khoa]
            if gt:
                trung_vi = f"{gt[0]:.1f}".replace(".", "{,}")
                lon_nhat = f"{gt[1]:.1f}".replace(".", "{,}")
                dong.append(f"{nhan} & {trung_vi}~ms & {lon_nhat}~ms \\\\")
            else:
                dong.append(f"{nhan} & \\cando{{ms}} & \\cando{{ms}} \\\\")
        dong.append("}")

        # Con so dung trong van xuoi. Thieu so nao thi giu gia tri mac dinh trong do-an.tex.
        def so(gt, chu_so=0):
            return f"{gt:.{chu_so}f}".replace(".", "{,}")

        def lenh(ten, gia_tri):
            if gia_tri is not None:
                dong.append(f"\\renewcommand{{\\{ten}}}{{{gia_tri}}}")

        mot, nhieu = ket_qua["mot_mat"], ket_qua["nhieu_mat"]
        lenh("HnMotMat", so(mot[0]) if mot else None)
        lenh("HnNhieuMat", so(nhieu[0]) if nhieu else None)
        lenh("HnSoMat", phu["so_mat"])
        if mot and nhieu and phu["so_mat"] and phu["so_mat"] > 1:
            lenh("HnMoiMatThem", so((nhieu[0] - mot[0]) / (phu["so_mat"] - 1)))
        lenh("HnTruyVan", so(ket_qua["truy_van"][0], 1) if ket_qua["truy_van"] else None)
        lenh("HnChongGiaMao", so(ket_qua["chong_gia_mao"][0], 1) if ket_qua["chong_gia_mao"] else None)
        lenh("HnTronVen", so(ket_qua["tron_ven"][0]) if ket_qua["tron_ven"] else None)
        lenh("HnSoVector", phu["so_vector"])
        lenh("HnGonMotMat", so(phu["gon_mot"]) if phu["gon_mot"] else None)
        lenh("HnGonNhieuMat", so(phu["gon_nhieu"]) if phu["gon_nhieu"] else None)
        if mot and phu["gon_mot"]:
            lenh("HnGiamMotMat", so(100 * (1 - phu["gon_mot"] / mot[0])))
        if nhieu and phu["gon_nhieu"]:
            lenh("HnGiamNhieuMat", so(100 * (1 - phu["gon_nhieu"] / nhieu[0])))
        lenh("HnSoLan", args.lan)
        lenh("HnNgayDo", time.strftime("%d/%m/%Y"))

        FILE_KET_QUA.parent.mkdir(parents=True, exist_ok=True)
        FILE_KET_QUA.write_text("\n".join(dong) + "\n", encoding="utf-8")
        print(f"\nDa ghi {FILE_KET_QUA}")

    thieu = [nhan for khoa, nhan in DONG_BANG if ket_qua[khoa] is None]
    if thieu:
        print("\nChua do duoc: " + "; ".join(thieu))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
