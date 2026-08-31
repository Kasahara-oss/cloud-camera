# -*- coding: utf-8 -*-
# ラズパイから届くCSVを確実に保存するためだけの独立した裏口プログラムです
import os
import sys
import cgi

print("Content-Type: text/plain\n")

try:
    form = cgi.FieldStorage()
    if "file" in form:
        fileitem = form["file"]
        if fileitem.file:
            # ラズパイから送られてきたCSVの中身をそのまま保存
            with open("qzss_data.csv", "wb") as f:
                f.write(fileitem.file.read())
            print("SUCCESS")
            sys.exit(0)
    print("ERROR: No file found")
except Exception as e:
    print(f"ERROR: {e}")
