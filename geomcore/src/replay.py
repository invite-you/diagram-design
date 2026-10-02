from __future__ import annotations
from pathlib import Path
import json

COL={
"paper":"#ffffff","normal":"#ffffff","zone":"#fafafa","header":"#e9ebee","focal":"#fff2e9","focalsoft":"#fde9db",
"series":"#dfe4ea","series2":"#d7e4dd","series3":"#e6dfeb","optional":"#ffffff","security":"#f3e5e5","chip":"#f1f2f4",
"grid":"none","axis":"none","edge":"none","link":"none","muted":"none","ink":"#2d3142","papertext":"#ffffff","text":"#2d3142","legend":"#fafafa",
"heat0":"#f7f7f7","heat1":"#e5e5e5","heat2":"#c8c8c8","heat3":"#929292","heat4":"#595959"}
STROKE={"focal":"#eb6c36","link":"#315f91","security":"#9b4d4d","muted":"#868a93","grid":"#d9dadd","axis":"#555965","edge":"#737782","ink":"#2d3142"}

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def marker_attrs(mark):
    return {
      "arrow":' marker-end="url(#arrow)"',
      "open":' marker-end="url(#open)"',
      "triangle":' marker-end="url(#triangle)"',
      "diamond-filled":' marker-end="url(#diamond-filled)"',
      "diamond-hollow":' marker-end="url(#diamond-hollow)"',
      "both":' marker-start="url(#arrow)" marker-end="url(#arrow)"',
    }.get(mark,"")

DEFS='''<defs>
<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="#737782"/></marker>
<marker id="triangle" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="#fff" stroke="#555965"/></marker>
<marker id="diamond-filled" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M1 6 L6 1 L11 6 L6 11 Z" fill="#555965"/></marker>
<marker id="diamond-hollow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M1 6 L6 1 L11 6 L6 11 Z" fill="#fff" stroke="#555965"/></marker>
<marker id="open" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9" fill="none" stroke="#555965"/></marker>
</defs>'''

def render(ir):
    W,H=ir["canvas"]["w"],ir["canvas"]["h"]
    body=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',DEFS,
          '<rect width="100%" height="100%" fill="#f5f5f5"/>']
    for p in ir["primitives"]:
        k=p["kind"]; f=esc(p["feature"]); role=p.get("role","normal")
        stroke=STROKE.get(role,"#777b86"); fill=COL.get(role,"#ffffff")
        if k=="rect":
            body.append(f'<rect data-feature="{f}" x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" rx="{p.get("rx",0)}" fill="{fill}" stroke="{STROKE.get(role,stroke)}" stroke-width="1"/>')
        elif k=="circle":
            fv="none" if role in ("grid","axis","edge","muted","link") else fill
            body.append(f'<circle data-feature="{f}" cx="{p["cx"]}" cy="{p["cy"]}" r="{p["r"]}" fill="{fv}" stroke="{stroke}" stroke-width="1.2"/>')
        elif k=="text":
            color="#fff" if role=="papertext" else ("#eb6c36" if role=="focal" else "#2d3142")
            body.append(f'<text data-feature="{f}" x="{p["x"]}" y="{p["y"]}" font-family="sans-serif" font-size="{p.get("size",12)}" text-anchor="{p.get("anchor","middle")}" fill="{color}">{esc(p["text"])}</text>')
        elif k=="line":
            dash=f' stroke-dasharray="{p["dash"]}"' if p.get("dash") else ""
            body.append(f'<line data-feature="{f}" x1="{p["x1"]}" y1="{p["y1"]}" x2="{p["x2"]}" y2="{p["y2"]}" stroke="{STROKE.get(role,"#737782")}" stroke-width="1.3"{dash}{marker_attrs(p.get("marker"))}/>')
        elif k=="polyline":
            dash=f' stroke-dasharray="{p["dash"]}"' if p.get("dash") else ""
            pts=" ".join(f"{x},{y}" for x,y in p["points"])
            body.append(f'<polyline data-feature="{f}" points="{pts}" fill="none" stroke="{STROKE.get(role,"#737782")}" stroke-width="1.4"{dash}{marker_attrs(p.get("marker"))}/>')
        elif k=="polygon":
            pts=" ".join(f"{x},{y}" for x,y in p["points"])
            body.append(f'<polygon data-feature="{f}" points="{pts}" fill="{fill}" fill-opacity="0.75" stroke="{stroke if role!="normal" else "#777b86"}" stroke-width="1.2"/>')
        elif k=="path":
            dash=f' stroke-dasharray="{p["dash"]}"' if p.get("dash") else ""
            body.append(f'<path data-feature="{f}" d="{p["d"]}" fill="{fill if p.get("fill") else "none"}" fill-opacity="0.45" stroke="{STROKE.get(role,"#737782")}" stroke-width="1.4"{dash}{marker_attrs(p.get("marker"))}/>')
    body.append("</svg>")
    return "\n".join(body)

def validate(ir):
    W,H=ir["canvas"]["w"],ir["canvas"]["h"]; issues=[]
    for p in ir["primitives"]:
        if p["kind"]=="rect":
            if p["w"]<=0 or p["h"]<=0: issues.append([p["id"],"nonpositive_rect"])
            if p["x"]<-2 or p["y"]<-2 or p["x"]+p["w"]>W+2 or p["y"]+p["h"]>H+2: issues.append([p["id"],"out_of_bounds"])
        elif p["kind"]=="circle":
            if p["cx"]-p["r"]<-2 or p["cy"]-p["r"]<-2 or p["cx"]+p["r"]>W+2 or p["cy"]+p["r"]>H+2: issues.append([p["id"],"out_of_bounds"])
    return issues

def replay(geometry_dir, output_dir):
    geometry_dir=Path(geometry_dir); output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    count=0
    for p in sorted(geometry_dir.glob("*.json")):
        ir=json.loads(p.read_text(encoding="utf-8"))
        issues=validate(ir)
        if issues: raise RuntimeError(f"{p.name}: {issues}")
        (output_dir/(p.stem+".svg")).write_text(render(ir),encoding="utf-8")
        count+=1
    return count

if __name__=="__main__":
    import sys
    n=replay(sys.argv[1],sys.argv[2])
    print(f"PASS {n} fixtures")
