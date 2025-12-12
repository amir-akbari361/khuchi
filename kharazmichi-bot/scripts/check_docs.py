"""
Quick diagnostic to check Word file contents
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from docx import Document
import docx2txt

# Check one file
file_path = r"d:\khuchi\kharazmichi-bot\knowledge\دانشکده فنی و مهندسی.docx"

print(f"Checking: {file_path}\n")
print("="*60)

# Method 1: docx2txt
try:
    text1 = docx2txt.process(file_path)
    print(f"Method 1 (docx2txt): {len(text1)} characters")
    print(f"Preview:\n{text1[:500]}")
except Exception as e:
    print(f"Method 1 failed: {e}")

print("\n" + "="*60 + "\n")

# Method 2: python-docx
try:
    doc = Document(file_path)
    text2 = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    print(f"Method 2 (python-docx): {len(text2)} characters")
    print(f"Preview:\n{text2[:500]}")
except Exception as e:
    print(f"Method 2 failed: {e}")
