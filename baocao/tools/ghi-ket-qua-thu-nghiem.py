"""Doc phieu dem tay trong baocao/do-thu-nghiem/ -> sinh 2 bang cua Chuong 5.

Hai thi nghiem nay phai co nguoi that ngoi truoc camera nen khong tu dong hoa duoc.
Nguoi do dem tay vao 2 file CSV, script nay tinh ti le va sinh file .tex:

    do-chinh-xac.csv    -> auto/bang-do-chinh-xac.tex
    chong-gia-mao.csv   -> auto/bang-chong-gia-mao.tex

Chay:
    python baocao/tools/ghi-ket-qua-thu-nghiem.py

Dong nao con trong thi bang van giu o "CAN BO SUNG" cho dong do, khong bia so.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

BAOCAO_DIR = Path(__file__).resolve().parents[1]
THU_MUC_PHIEU = BAOCAO_DIR / "do-thu-nghiem"
AUTO_DIR = BAOCAO_DIR / "auto"

# Console Windows mac dinh khong phai UTF-8: in ten dieu kien co dau se vo neu khong
# dat lai. errors="replace" de khong bao gio chet vi mot ky tu khong in duoc.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def so_nguyen(gia_tri: str) -> int | None:
    gia_tri = (gia_tri or "").strip()
    if not gia_tri:
        return None
    try:
        return int(gia_tri)
    except ValueError:
        print(f"[!] Khong doc duoc so: {gia_tri!r}")
        return None


def doc_phieu(ten_file: str, cot: tuple[str, str, str]) -> list[dict]:
    duong_dan = THU_MUC_PHIEU / ten_file
    if not duong_dan.exists():
        print(f"[!] Thieu phieu {duong_dan}")
        return []
    with duong_dan.open(encoding="utf-8-sig", newline="") as f:
        dong = []
        for hang in csv.DictReader(f):
            dong.append({
                "nhan": (hang.get(cot[0]) or "").strip(),
                "tong": so_nguyen(hang.get(cot[1], "")),
                "dat": so_nguyen(hang.get(cot[2], "")),
            })
    return dong


def ti_le(dat: int, tong: int) -> str:
    return f"{dat / tong * 100:.1f}".replace(".", "{,}") + r"\%"


def sinh_bang_do_chinh_xac(dong: list[dict]) -> str:
    # Boc thanh lenh: bao cao nap file nay o preamble roi goi \BangDoChinhXac trong
    # than bang, vi tabularx khong chiu duoc \input ben trong.
    ra = ["% File nay do baocao/tools/ghi-ket-qua-thu-nghiem.py sinh ra. KHONG SUA TAY.",
          "% Nguon: baocao/do-thu-nghiem/do-chinh-xac.csv",
          r"\renewcommand{\BangDoChinhXac}{%"]
    tong_thu = tong_dung = 0
    du_so_lieu = True
    for h in dong:
        if h["tong"] and h["dat"] is not None:
            tong_thu += h["tong"]
            tong_dung += h["dat"]
            ra.append(f"{h['nhan']} & {h['tong']} & {h['dat']} & {ti_le(h['dat'], h['tong'])} \\\\")
        else:
            du_so_lieu = False
            ra.append(f"{h['nhan']} & \\cando{{n}} & \\cando{{n}} & \\cando{{\\%}} \\\\")
    ra.append(r"\midrule")
    if du_so_lieu and tong_thu:
        ra.append(f"\\textbf{{Tổng hợp}} & {tong_thu} & {tong_dung} & "
                  f"{ti_le(tong_dung, tong_thu)} \\\\")
    else:
        ra.append(r"\textbf{Tổng hợp} & \cando{n} & \cando{n} & \cando{\%} \\")
    ra.append("}")
    return "\n".join(ra) + "\n"


def sinh_bang_chong_gia_mao(dong: list[dict]) -> str:
    ra = ["% File nay do baocao/tools/ghi-ket-qua-thu-nghiem.py sinh ra. KHONG SUA TAY.",
          "% Nguon: baocao/do-thu-nghiem/chong-gia-mao.csv",
          r"\renewcommand{\BangChongGiaMao}{%"]
    for h in dong:
        if h["tong"] and h["dat"] is not None:
            ra.append(f"{h['nhan']} & {h['tong']} & {h['dat']} \\\\")
        else:
            ra.append(f"{h['nhan']} & \\cando{{n}} & \\cando{{n}} \\\\")
    ra.append("}")
    return "\n".join(ra) + "\n"


def main() -> int:
    do_chinh_xac = doc_phieu("do-chinh-xac.csv", ("dieu_kien", "so_lan_thu", "nhan_dung"))
    chong_gia_mao = doc_phieu("chong-gia-mao.csv",
                              ("kieu_tan_cong", "so_lan_thu", "so_lan_chan"))
    if not do_chinh_xac and not chong_gia_mao:
        return 1

    AUTO_DIR.mkdir(parents=True, exist_ok=True)
    if do_chinh_xac:
        (AUTO_DIR / "bang-do-chinh-xac.tex").write_text(
            sinh_bang_do_chinh_xac(do_chinh_xac), encoding="utf-8")
    if chong_gia_mao:
        (AUTO_DIR / "bang-chong-gia-mao.tex").write_text(
            sinh_bang_chong_gia_mao(chong_gia_mao), encoding="utf-8")

    con_trong = [h["nhan"] for h in do_chinh_xac + chong_gia_mao
                 if not h["tong"] or h["dat"] is None]
    print(f"Da ghi bang vao {AUTO_DIR}")
    if con_trong:
        print("Cac dong con trong (van in CAN BO SUNG): " + "; ".join(con_trong))
        return 1
    print("Da du so lieu cho ca hai bang.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
