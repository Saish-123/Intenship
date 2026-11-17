"""Subset the web fonts to the characters this site uses.\nneeds: pip install fonttools brotli ; npm install @fontsource/bitter @fontsource/source-sans-3\nrun from the project root: python tools/subset_fonts.py"""
import re, glob, subprocess, os
from fontTools.ttLib import TTFont
SRC=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","src")
text=""
for f in glob.glob(SRC+"/*.html")+glob.glob(SRC+"/js/*.js")+glob.glob(SRC+"/css/*.css"):
    text+=open(f,encoding="utf-8").read()
# characters the site really uses + a safety net of common typography for future edits
used={ord(c) for c in text if ord(c)>=0x20}
safety=set(range(0x20,0x7F))|{0xA0,0xA9,0xB7,0x2013,0x2014,0x2018,0x2019,0x201C,0x201D,0x2026,0x2212,0x2022}
cps=sorted(used|safety)
FONTS={"source-sans-3-400":"source-sans-3/files/source-sans-3-latin-400-normal.woff2","source-sans-3-600":"source-sans-3/files/source-sans-3-latin-600-normal.woff2",
       "bitter-800":"bitter/files/bitter-latin-800-normal.woff2"}
report={}
for name,rel in FONTS.items():
    src="node_modules/@fontsource/"+rel; out=f"{SRC}/fonts/{name}.woff2"
    have=set(TTFont(src).getBestCmap().keys()); want=[c for c in cps if c in have]
    missing=[chr(c) for c in cps if c not in have and c>0x7F]
    unicodes=",".join(f"U+{c:04X}" for c in want)
    subprocess.run(["pyftsubset",src,f"--unicodes={unicodes}","--flavor=woff2","--layout-features=kern,liga,ccmp,locl,mark,mkmk","--no-hinting","--desubroutinize",f"--output-file={out}"],check=True)
    report[name]=(os.path.getsize(src),os.path.getsize(out),len(want),"".join(missing))
for k,v in report.items(): print(f"{k:20} original {v[0]:6} B -> subset {v[1]:6} B  glyph codepoints {v[2]}  not in font: {v[3]!r}")
print("total original",sum(v[0] for v in report.values()),"subset",sum(v[1] for v in report.values()))
