"""Doi mat khau cho toan bo tai khoan truoc khi mo he thong ra Internet.

Du lieu mau (seed.py) dung mat khau rat yeu - admin123, gv123, sv123. De nguyen
roi mo link cong khai thi nguoi la dang nhap duoc va xem het anh khuon mat, diem
danh cua sinh vien.

Cach chay (tren may chu, trong container backend):
    docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env \
        exec backend python tools/doi_mat_khau.py

Mat khau moi duoc ghi ra tep mat_khau_moi.csv trong thu muc dang chay. Tep nay
chua mat khau dang chu ro: doc xong, gui cho tung nguoi roi XOA di.

Tuy chon:
    --chi-xem        chi liet ke tai khoan se bi doi, khong ghi gi vao CSDL
    --do-dai N       do dai mat khau (mac dinh 14)
    --vai-tro X,Y    chi doi cho cac vai tro nay (mac dinh: tat ca)
"""
import argparse
import csv
import os
import secrets
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db import models  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402

# Bo ky tu de doc khi phai go lai hoac doc qua dien thoai: bo 0/O, 1/l/I.
ALPHABET = ("".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
            + "@#%+=?")


def sinh_mat_khau(do_dai: int) -> str:
    """Mat khau ngau nhien, bao dam co du chu hoa, chu thuong, so va ky tu dac biet."""
    while True:
        mk = "".join(secrets.choice(ALPHABET) for _ in range(do_dai))
        if (any(c.isupper() for c in mk) and any(c.islower() for c in mk)
                and any(c.isdigit() for c in mk) and any(not c.isalnum() for c in mk)):
            return mk


def main() -> int:
    parser = argparse.ArgumentParser(description="Doi mat khau hang loat")
    parser.add_argument("--chi-xem", action="store_true", help="khong ghi gi vao CSDL")
    parser.add_argument("--do-dai", type=int, default=14)
    parser.add_argument("--vai-tro", default="", help="loc theo vai tro, cach nhau bang dau phay")
    parser.add_argument("--ra", default="mat_khau_moi.csv")
    args = parser.parse_args()

    if args.do_dai < 10:
        print("Mat khau ngan hon 10 ky tu thi doi lam gi.", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        query = db.query(models.User).order_by(models.User.role, models.User.email)
        if args.vai_tro:
            vai_tro = [v.strip() for v in args.vai_tro.split(",") if v.strip()]
            query = query.filter(models.User.role.in_(vai_tro))
        users = query.all()

        if not users:
            print("Khong co tai khoan nao khop.")
            return 1

        print(f"{len(users)} tai khoan se duoc doi mat khau:")
        theo_vai_tro: dict[str, int] = {}
        for u in users:
            theo_vai_tro[u.role] = theo_vai_tro.get(u.role, 0) + 1
        for role, n in sorted(theo_vai_tro.items()):
            print(f"  {role}: {n}")

        if args.chi_xem:
            print("\n(--chi-xem: khong ghi gi vao CSDL)")
            return 0

        rows = []
        for u in users:
            mk = sinh_mat_khau(args.do_dai)
            u.password_hash = hash_password(mk)
            # Thu hoi moi token dang con hieu luc cua tai khoan nay.
            u.token_version = (u.token_version or 0) + 1
            rows.append({"email": u.email, "ho_ten": u.full_name, "vai_tro": u.role,
                         "mat_khau_moi": mk})

        # Thu hoi ca refresh token da phat, neu bang nay ton tai.
        db.query(models.RefreshToken).delete()
        db.commit()

        with open(args.ra, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "ho_ten", "vai_tro", "mat_khau_moi"])
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nDa doi xong. Mat khau moi ghi o: {os.path.abspath(args.ra)}")
        print("Gui cho tung nguoi roi XOA tep nay - no dang de mat khau dang chu ro.")
        print("Moi phien dang nhap cu da bi thu hoi, tat ca phai dang nhap lai.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
