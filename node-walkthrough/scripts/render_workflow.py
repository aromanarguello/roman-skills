#!/usr/bin/env python3
"""Render a sparse interactive node walkthrough from a JSON workflow spec."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
LANES = {"left", "center", "right"}
STATUSES = {"done", "next", "pending"}
ICONS = {"trigger", "clock", "file", "search", "quote", "sparkle", "check", "git", "brain", "shield", "link", "person", "database"}


def text_field(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValueError(f"{name} must be {maximum} characters or fewer")
    return cleaned


def validate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("spec must be a JSON object")
    title = text_field(raw.get("title"), "title", 64)
    state = text_field(raw.get("state", "CURRENT"), "state", 16).upper()
    boundary_raw = raw.get("boundary", "")
    if not isinstance(boundary_raw, str) or len(boundary_raw.strip()) > 96:
        raise ValueError("boundary must be a string of 96 characters or fewer")
    boundary = boundary_raw.strip()

    nodes_raw = raw.get("nodes")
    if not isinstance(nodes_raw, list) or not 2 <= len(nodes_raw) <= 10:
        raise ValueError("nodes must contain between 2 and 10 items")
    nodes: list[dict[str, Any]] = []
    ids: set[str] = set()
    row_lanes: set[tuple[int, str]] = set()
    for index, item in enumerate(nodes_raw):
        if not isinstance(item, dict):
            raise ValueError(f"nodes[{index}] must be an object")
        node_id = text_field(item.get("id"), f"nodes[{index}].id", 40)
        if not ID_RE.fullmatch(node_id):
            raise ValueError(f"nodes[{index}].id has an invalid format")
        if node_id in ids:
            raise ValueError(f"duplicate node id: {node_id}")
        ids.add(node_id)
        row = item.get("row")
        if not isinstance(row, int) or row < 0 or row > 20:
            raise ValueError(f"nodes[{index}].row must be an integer from 0 to 20")
        lane = item.get("lane", "center")
        if lane not in LANES:
            raise ValueError(f"nodes[{index}].lane must be left, center, or right")
        if (row, lane) in row_lanes:
            raise ValueError(f"row {row} contains more than one {lane} node")
        row_lanes.add((row, lane))
        icon = item.get("icon", "file")
        if icon not in ICONS:
            raise ValueError(f"nodes[{index}].icon is unsupported: {icon}")
        status = item.get("status", "next")
        if status not in STATUSES:
            raise ValueError(f"nodes[{index}].status must be done, next, or pending")
        nodes.append({
            "id": node_id,
            "title": text_field(item.get("title"), f"nodes[{index}].title", 42),
            "subtitle": text_field(item.get("subtitle"), f"nodes[{index}].subtitle", 54),
            "detail": text_field(item.get("detail"), f"nodes[{index}].detail", 560),
            "icon": icon,
            "row": row,
            "lane": lane,
            "status": status,
        })

    edges_raw = raw.get("edges")
    if not isinstance(edges_raw, list) or not edges_raw:
        raise ValueError("edges must be a non-empty list")
    edges: list[list[str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges_raw):
        if not isinstance(edge, list) or len(edge) != 2 or not all(isinstance(part, str) for part in edge):
            raise ValueError(f"edges[{index}] must be [source_id, target_id]")
        source, target = edge
        if source not in ids or target not in ids:
            raise ValueError(f"edges[{index}] references an unknown node")
        if source == target:
            raise ValueError(f"edges[{index}] cannot connect a node to itself")
        pair = (source, target)
        if pair in seen_edges:
            raise ValueError(f"duplicate edge: {source} -> {target}")
        seen_edges.add(pair)
        edges.append([source, target])
    return {"title": title, "state": state, "boundary": boundary, "nodes": nodes, "edges": edges}


HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>
:root{color-scheme:dark;--page:#050506;--canvas:#111017;--border:#363443;--line:#514c59;--text:#f1eff5;--muted:#8f8b98;--pink:#d76baa;--blue:#739df8;--green:#70c9a5;--amber:#dba263}*{box-sizing:border-box}body{min-width:320px;min-height:100dvh;margin:0;display:grid;place-items:center;padding:28px;color:var(--text);background:var(--page);font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button{font:inherit}.window{width:min(980px,96vw);height:min(820px,calc(100dvh - 56px));min-height:680px;overflow:hidden;border:1px solid #3a3742;border-radius:18px;background:var(--canvas);box-shadow:0 36px 100px rgba(0,0,0,.72)}
.titlebar{position:relative;z-index:10;height:46px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 16px;border-bottom:1px solid #2b2932;background:#17161d;color:#86818e;font-size:12px}.lights{display:flex;gap:7px}.light{width:10px;height:10px;border-radius:50%}.red{background:#ff6259}.yellow{background:#ffbd2e}.green{background:#28c840}.title{color:#aaa5b1;font-weight:600}.state{justify-self:end;color:#696571;font:10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em}
.workspace{position:relative;height:calc(100% - 46px);overflow:hidden;background-color:var(--canvas);background-image:radial-gradient(circle,#292633 1px,transparent 1.1px);background-size:20px 20px;isolation:isolate}.workspace:before{position:absolute;inset:0;z-index:-1;background:radial-gradient(circle at 50% 42%,rgba(215,107,170,.05),transparent 38%);content:""}.workspace-label{position:absolute;top:16px;left:18px;color:#686471;font:600 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase}
.paths{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.path{fill:none;stroke:var(--line);stroke-width:1.5;vector-effect:non-scaling-stroke}.path.live{stroke:url(#route)}.pulse{fill:none;stroke:#f5c1df;stroke-width:2;stroke-linecap:round;stroke-dasharray:2 220;animation:travel 4.8s linear infinite;filter:drop-shadow(0 0 5px var(--pink));vector-effect:non-scaling-stroke}@keyframes travel{to{stroke-dashoffset:-222}}.joint{fill:#4b4754;stroke:#24222a;stroke-width:2}
.node{position:absolute;z-index:3;width:252px;min-height:58px;display:grid;grid-template-columns:30px minmax(0,1fr) auto;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;color:var(--text);background:rgba(24,23,32,.98);box-shadow:0 8px 22px rgba(0,0,0,.18);text-align:left;cursor:pointer;transform:translate(-50%,-50%);transition:opacity 180ms ease,border-color 180ms ease,box-shadow 180ms ease,transform 180ms ease}.node:hover{border-color:#5c5767}.node:focus-visible,.control:focus-visible{outline:3px solid rgba(115,157,248,.72);outline-offset:3px}.node.active{z-index:8;border-color:var(--pink);box-shadow:0 0 0 1px rgba(215,107,170,.22),0 18px 44px rgba(0,0,0,.5);transform:translate(-50%,-50%) scale(1.025)}.node.dim{opacity:.14}.icon{width:30px;height:30px;display:grid;place-items:center;border-radius:7px;color:var(--pink);background:rgba(215,107,170,.1)}.icon.blue{color:var(--blue);background:rgba(115,157,248,.1)}.icon.green{color:var(--green);background:rgba(112,201,165,.1)}.icon svg{width:16px;height:16px;stroke-width:1.8}.copy{min-width:0}.name{display:block;overflow:hidden;color:#e8e5ec;font-size:13px;font-weight:650;text-overflow:ellipsis;white-space:nowrap}.meta{display:block;margin-top:3px;overflow:hidden;color:var(--muted);font:10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;text-overflow:ellipsis;white-space:nowrap}.status{color:var(--green);font-size:13px}
.boundary{position:absolute;z-index:4;left:50%;bottom:58px;display:none;align-items:center;gap:8px;max-width:calc(100% - 28px);padding:7px 10px;overflow:hidden;border:1px solid rgba(219,162,99,.3);border-radius:7px;color:#b7a58e;background:rgba(37,28,20,.7);font-size:10px;text-overflow:ellipsis;transform:translateX(-50%);white-space:nowrap;transition:opacity 180ms ease}.boundary.show{display:flex}.boundary.dim{opacity:.12}.boundary-dot{width:6px;height:6px;flex:none;border-radius:50%;background:var(--amber)}
.controls{position:absolute;z-index:12;right:0;bottom:0;left:0;height:46px;display:flex;align-items:center;gap:10px;padding:0 14px;border-top:1px solid #2d2a34;background:rgba(18,17,23,.96)}.control{min-width:36px;min-height:32px;padding:0 11px;border:1px solid #3c3845;border-radius:7px;color:#aaa5b0;background:#1c1a22;cursor:pointer;transition:color 160ms ease,border-color 160ms ease,background 160ms ease}.control:hover{color:#f2eff5;border-color:#5b5565;background:#24212b}.control.primary{color:#f5edf2;border-color:rgba(215,107,170,.48);background:rgba(215,107,170,.13)}.control[disabled]{opacity:.35;cursor:default}.timeline{position:relative;height:2px;flex:1;background:#3a3540}.timeline-fill{width:0;height:100%;background:var(--pink);transition:width 220ms ease}.timeline-dots{position:absolute;inset:-3px 0 auto;display:flex;justify-content:space-between}.timeline-dot{width:8px;height:8px;border:2px solid #17151c;border-radius:50%;background:#514b58;transition:background 180ms ease}.timeline-dot.done{background:var(--pink)}.timeline-dot.current{background:var(--green)}.counter{width:48px;color:#77717e;font:10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;text-align:right}
.tour{position:absolute;z-index:20;top:18px;left:18px;width:292px;padding:16px;border:1px solid #443e4a;border-radius:8px;background:rgba(25,23,31,.985);box-shadow:0 20px 60px rgba(0,0,0,.6);opacity:0;pointer-events:none;transform:translateY(-8px);transition:opacity 180ms ease,transform 180ms ease}.tour.show{opacity:1;pointer-events:auto;transform:translateY(0)}.tour-step{color:var(--pink);font:650 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase}.tour h1{margin:10px 0 7px;font-size:15px;letter-spacing:-.01em}.tour p{margin:0;color:#aaa5b0;font-size:12px;line-height:1.5}.tour-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:14px}.tour-actions{display:flex;gap:7px}.tour .control{min-height:34px;font-size:11px}
@media(max-width:720px){body{padding:0}.window{width:100vw;height:100dvh;min-height:680px;border:0;border-radius:0}.state{display:none}.node{width:210px}.tour{top:auto;right:12px;bottom:58px;left:12px;width:auto}.name{font-size:12px}}@media(max-width:520px){.node{width:176px;grid-template-columns:26px minmax(0,1fr) auto;gap:7px;padding:8px}.icon{width:26px;height:26px}.node[data-lane="left"]{left:25%!important}.node[data-lane="right"]{left:75%!important}#back,#next{padding-inline:8px}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}.pulse{display:none}}
</style></head><body><main class="window"><header class="titlebar"><div class="lights" aria-hidden="true"><i class="light red"></i><i class="light yellow"></i><i class="light green"></i></div><div class="title" id="windowTitle"></div><div class="state" id="windowState"></div></header><section class="workspace" id="workspace" aria-label="Interactive workflow diagram"><div class="workspace-label">Workflow</div><svg class="paths" id="paths" aria-hidden="true"><defs><linearGradient id="route" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#514c59"/><stop offset=".5" stop-color="#a15482"/><stop offset="1" stop-color="#5c8e7b"/></linearGradient></defs><g id="edgeLayer"></g></svg><div class="boundary" id="boundary"><span class="boundary-dot"></span><span id="boundaryText"></span></div><aside class="tour" id="tour" aria-live="polite" aria-labelledby="tourTitle"><div class="tour-step" id="tourStep"></div><h1 id="tourTitle"></h1><p id="tourText"></p><div class="tour-footer"><button class="control" id="close" type="button">Close</button><div class="tour-actions"><button class="control" id="back" type="button">Previous</button><button class="control primary" id="next" type="button">Next</button></div></div></aside><footer class="controls"><button class="control primary" id="start" type="button">Walkthrough</button><div class="timeline" aria-hidden="true"><div class="timeline-fill" id="fill"></div><div class="timeline-dots" id="dots"></div></div><span class="counter" id="counter"></span></footer></section></main><script id="workflowSpec" type="application/json">__SPEC__</script>
<script>
const spec=JSON.parse(document.getElementById("workflowSpec").textContent),icons={trigger:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="m13 2-9 12h7l-1 8 9-12h-7l1-8Z"/></svg>',clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',file:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M6 3h9l3 3v15H6zM15 3v4h4M9 12h6M9 16h4"/></svg>',search:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5M7 10h6"/></svg>',quote:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M6 7h5v6H7v4H4v-7a3 3 0 0 1 2-3Zm10 0h4v6h-4v4h-3v-7a3 3 0 0 1 3-3Z"/></svg>',sparkle:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 3 9 9l-6 3 6 3 3 6 3-6 6-3-6-3-3-6Z"/></svg>',check:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="m5 12 4 4L19 6"/><path d="M3 3h18v18H3z"/></svg>',git:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="3"/><path d="M3 12h6M15 12h6M12 3v6M12 15v6"/></svg>',brain:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-2 3 3 3 0 0 0 2 3v1a3 3 0 0 0 3 3M15 4a3 3 0 0 1 3 3v1a3 3 0 0 1 2 3 3 3 0 0 1-2 3v1a3 3 0 0 1-3 3M9 4v16M15 4v16M9 8h3M12 12h3M9 16h3"/></svg>',shield:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/></svg>',link:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>',person:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',database:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 2 3.6 3 8 3s8-1 8-3V5M4 12v7c0 2 3.6 3 8 3s8-1 8-3v-7"/></svg>'};
const laneX={left:33,center:50,right:67},workspace=document.getElementById("workspace"),edgeLayer=document.getElementById("edgeLayer");document.getElementById("windowTitle").textContent=spec.title;document.getElementById("windowState").textContent=spec.state;const boundary=document.getElementById("boundary");if(spec.boundary){boundary.classList.add("show");document.getElementById("boundaryText").textContent=spec.boundary}const rows=[...new Set(spec.nodes.map(n=>n.row))].sort((a,b)=>a-b),rowIndex=new Map(rows.map((row,index)=>[row,index])),topMin=8,topMax=spec.boundary?82:88;
const nodes=spec.nodes.map((node,index)=>{const button=document.createElement("button");button.type="button";button.className="node";button.dataset.step=String(index);button.dataset.id=node.id;button.dataset.lane=node.lane;button.style.left=`${laneX[node.lane]}%`;button.style.top=`${rows.length===1?48:topMin+(topMax-topMin)*(rowIndex.get(node.row)/(rows.length-1))}%`;const icon=document.createElement("span");icon.className=`icon ${node.lane!=="center"?"blue":node.status==="done"?"green":""}`;icon.innerHTML=icons[node.icon];const copy=document.createElement("span");copy.className="copy";const name=document.createElement("span");name.className="name";name.textContent=node.title;const meta=document.createElement("span");meta.className="meta";meta.textContent=node.subtitle;copy.append(name,meta);const status=document.createElement("span");status.className="status";status.textContent=node.status==="done"?"✓":node.status==="next"?"→":"·";button.append(icon,copy,status);workspace.appendChild(button);return button});
function draw(){edgeLayer.replaceChildren();const root=workspace.getBoundingClientRect();spec.edges.forEach((edge,index)=>{const source=nodes.find(n=>n.dataset.id===edge[0]).getBoundingClientRect(),target=nodes.find(n=>n.dataset.id===edge[1]).getBoundingClientRect(),x1=source.left+source.width/2-root.left,y1=source.bottom-root.top,x2=target.left+target.width/2-root.left,y2=target.top-root.top,mid=y1+(y2-y1)*.5;const path=document.createElementNS("http://www.w3.org/2000/svg","path");path.setAttribute("class","path live");path.setAttribute("d",Math.abs(x1-x2)<2?`M${x1} ${y1} L${x2} ${y2}`:`M${x1} ${y1} C${x1} ${mid} ${x2} ${mid} ${x2} ${y2}`);edgeLayer.appendChild(path);const joint=document.createElementNS("http://www.w3.org/2000/svg","circle");joint.setAttribute("class","joint");joint.setAttribute("cx",String(x1+(x2-x1)*.5));joint.setAttribute("cy",String(mid));joint.setAttribute("r","5");edgeLayer.appendChild(joint);if(index===0){const pulse=path.cloneNode();pulse.setAttribute("class","pulse");edgeLayer.appendChild(pulse)}})}requestAnimationFrame(draw);new ResizeObserver(draw).observe(workspace);
const tour=document.getElementById("tour"),tourStep=document.getElementById("tourStep"),tourTitle=document.getElementById("tourTitle"),tourText=document.getElementById("tourText"),back=document.getElementById("back"),next=document.getElementById("next"),counter=document.getElementById("counter"),fill=document.getElementById("fill"),dots=document.getElementById("dots");let current=-1;spec.nodes.forEach(()=>{const dot=document.createElement("i");dot.className="timeline-dot";dots.appendChild(dot)});counter.textContent=`0 / ${nodes.length}`;
function render(index){current=Math.max(0,Math.min(nodes.length-1,index));tour.classList.add("show");nodes.forEach((node,i)=>{node.classList.toggle("active",i===current);node.classList.toggle("dim",i!==current)});boundary.classList.add("dim");const item=spec.nodes[current];tourStep.textContent=`Step ${current+1} of ${nodes.length}`;tourTitle.textContent=item.title;tourText.textContent=item.detail;counter.textContent=`${current+1} / ${nodes.length}`;fill.style.width=`${nodes.length===1?100:current/(nodes.length-1)*100}%`;[...dots.children].forEach((dot,i)=>{dot.classList.toggle("done",i<current);dot.classList.toggle("current",i===current)});back.disabled=current===0;next.textContent=current===nodes.length-1?"Finish":"Next"}
function closeTour(){current=-1;tour.classList.remove("show");nodes.forEach(node=>node.classList.remove("active","dim"));boundary.classList.remove("dim");counter.textContent=`0 / ${nodes.length}`;fill.style.width="0";[...dots.children].forEach(dot=>dot.classList.remove("done","current"))}document.getElementById("start").addEventListener("click",()=>render(0));document.getElementById("close").addEventListener("click",closeTour);back.addEventListener("click",()=>render(current-1));next.addEventListener("click",()=>current===nodes.length-1?closeTour():render(current+1));nodes.forEach((node,index)=>node.addEventListener("click",()=>render(index)));document.addEventListener("keydown",event=>{if(current<0)return;if(event.key==="Escape")closeTour();if(event.key==="ArrowRight")next.click();if(event.key==="ArrowLeft"&&current>0)back.click()});
</script></body></html>'''


def render(spec: dict[str, Any]) -> str:
    encoded = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return HTML.replace("__TITLE__", html.escape(spec["title"])).replace("__SPEC__", encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.spec.open("r", encoding="utf-8") as handle:
        spec = validate(json.load(handle))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(spec), encoding="utf-8")
    print(f"Rendered {len(spec['nodes'])} nodes to {args.output}")


if __name__ == "__main__":
    main()
