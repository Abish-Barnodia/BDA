#!/usr/bin/env python3
"""
download_kaggle_dataset.py — Download Kaggle eCommerce dataset using kagglehub
ponytail: download, list files, and copy primary CSV to data/
"""
import os
import sys

# Set pure python protobuf implementation before importing kagglehub to support Python 3.14
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import shutil
import kagglehub

print("[*] Downloading abhayayare/e-commerce-dataset via kagglehub...")
path = kagglehub.dataset_download("abhayayare/e-commerce-dataset")
print("[+] Dataset downloaded to:", path)

files = os.listdir(path)
print("[*] Files in dataset:", files)

csv_files = [f for f in files if f.endswith(".csv")]
print("[*] Found CSV files:", csv_files)

os.makedirs("data", exist_ok=True)
for f in csv_files:
    src = os.path.join(path, f)
    dst = os.path.join("data", f)
    print(f"[*] Copying {src} -> {dst}")
    shutil.copyfile(src, dst)
    size_mb = os.path.getsize(dst) / (1024 * 1024)
    print(f"[+] Stored {dst} ({size_mb:.2f} MB)")

print("[+] Dataset acquisition complete!")
