"""Kiem tra tinh bo tai lieu LaTeX truoc khi bien dich.

Dung khi may khong cai TeX (hoac muon bat loi som truoc khi day len Overleaf).
Script KHONG bien dich, chi doc ma nguon .tex va bat nam loi hay gap nhat:

    1. \\begin{...} khong co \\end{...} tuong ung
    2. Lech dau ngoac nhon trong mot tep
    3. \\input tro toi tep khong ton tai
    4. \\ref khong co \\label, \\cite khong co trong refs.bib, muc bib khong ai trich
    5. Dau gach duoi chua thoat o che do van ban (loi "Missing $ inserted")

Chay:
    python baocao/tools/kiem-tra-tex.py

Thoat 0 neu sach, thoat 1 neu co van de. Khong thay the viec bien dich that:
loi trang, loi tran le, thieu phong chu... chi thay duoc khi chay latexmk.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

GOC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
loi: list[str] = []


def cac_file_tex(chinh: Path) -> list[Path]:
    """Duyet de quy theo \\input tu tep chinh, tra ve danh sach tep thuc su duoc nap."""
    da_xet: list[Path] = []
    hang_doi = [chinh]
    while hang_doi:
        f = hang_doi.pop(0)
        if f in da_xet:
            continue
        if not f.exists():
            loi.append(f"thieu tep duoc \\input: {f.relative_to(GOC) if GOC in f.parents else f}")
            continue
        da_xet.append(f)
        noi_dung = re.sub(r"(?<!\\)%.*", "", f.read_text(encoding="utf-8"))
        # \IfFileExists{...}{\input{...}}: tep tuy chon (vd bang so do hieu nang chi co
        # sau khi chay do_hieu_nang.py) - thieu cung khong phai loi.
        noi_dung = re.sub(r"\\IfFileExists\{[^}]*\}\{\\input\{[^}]*\}\}", "", noi_dung)
        for m in re.finditer(r"\\input\{([^}]+)\}", noi_dung):
            hang_doi.append(GOC / (m.group(1) + ".tex"))
    return da_xet


def kiem_tra(chinh: Path, nhan: str) -> None:
    files = cac_file_tex(chinh)
    print(f"\n=== {nhan}: {len(files)} tep ===")
    nhan_dinh_nghia: set[str] = set()
    nhan_tham_chieu: set[str] = set()
    khoa_cite: set[str] = set()

    for f in files:
        noi_dung = re.sub(r"(?<!\\)%.*", "", f.read_text(encoding="utf-8"))
        ten = f.relative_to(GOC)

        ngan_xep: list[tuple[str, int]] = []
        for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", noi_dung):
            if m.group(1) == "begin":
                ngan_xep.append((m.group(2), noi_dung[:m.start()].count("\n") + 1))
            elif not ngan_xep:
                loi.append(f"{ten}: \\end{{{m.group(2)}}} thua")
            elif ngan_xep[-1][0] != m.group(2):
                loi.append(f"{ten}: \\end{{{m.group(2)}}} khong khop \\begin{{{ngan_xep[-1][0]}}} "
                           f"o dong {ngan_xep[-1][1]}")
                ngan_xep.pop()
            else:
                ngan_xep.pop()
        for ten_mt, dong in ngan_xep:
            loi.append(f"{ten}: \\begin{{{ten_mt}}} dong {dong} chua duoc dong")

        lech = (noi_dung.count("{") - noi_dung.count("}")
                - (noi_dung.count("\\{") - noi_dung.count("\\}")))
        if lech != 0:
            loi.append(f"{ten}: lech {lech} dau ngoac nhon")

        nhan_dinh_nghia |= set(re.findall(r"\\label\{([^}]+)\}", noi_dung))
        # label={...} trong tuy chon cua listings cung sinh ra mot nhan
        nhan_dinh_nghia |= set(re.findall(r"label=\{([^}]+)\}", noi_dung))
        nhan_tham_chieu |= set(re.findall(r"\\ref\{([^}]+)\}", noi_dung))
        khoa_cite |= set(re.findall(r"\\cite\{([^}]+)\}", noi_dung))

        # Dau _ ngoai che do toan, ngoai khoi ma va ngoai \code{}
        sach = re.sub(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", "", noi_dung, flags=re.S)
        sach = re.sub(r"\\lstinputlisting(\[[^\]]*\])?\{[^}]*\}", "", sach, flags=re.S)
        sach = re.sub(r"\\begin\{(equation|algorithmic|align)\*?\}.*?\\end\{\1\*?\}", "",
                      sach, flags=re.S)
        sach = re.sub(r"\\\[.*?\\\]", "", sach, flags=re.S)
        sach = re.sub(r"\$[^$]*\$", "", sach)
        sach = re.sub(r"\\(code|url|texttt|lstinline)\{[^}]*\}", "", sach)
        for m in re.finditer(r"(?<!\\)_", sach):
            loi.append(f"{ten}: dau _ chua thoat, khoang dong {sach[:m.start()].count(chr(10)) + 1}")

    for x in sorted(nhan_tham_chieu - nhan_dinh_nghia):
        loi.append(f"{nhan}: \\ref{{{x}}} khong co \\label tuong ung")

    bib = GOC / "refs.bib"
    if bib.exists() and khoa_cite:
        co_san = set(re.findall(r"@\w+\{([^,]+),", bib.read_text(encoding="utf-8")))
        da_trich = {kk.strip() for k in khoa_cite for kk in k.split(",") if kk.strip()}
        for k in sorted(da_trich - co_san):
            loi.append(f"{nhan}: \\cite{{{k}}} khong co trong refs.bib")
        for k in sorted(co_san - da_trich):
            loi.append(f"{nhan}: muc refs.bib '{k}' chua duoc trich dan lan nao")

    print(f"  nhan: {len(nhan_dinh_nghia)}, tham chieu: {len(nhan_tham_chieu)}, "
          f"trich dan: {len(khoa_cite)}")


def main() -> int:
    for chinh, nhan in ((GOC / "do-an.tex", "Bao cao"), (GOC / "slide.tex", "Slide")):
        if chinh.exists():
            kiem_tra(chinh, nhan)

    print("\n" + "=" * 62)
    if loi:
        print(f"CO {len(loi)} VAN DE:")
        for x in loi:
            print("  -", x)
        return 1
    print("KHONG PHAT HIEN VAN DE (van phai bien dich that de chac chan)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
