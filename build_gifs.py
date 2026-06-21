#!/usr/bin/env python3
"""
Generate 5 animated GIFs of the Anthropic agent-workflow patterns, in the deck's
ivory/clay theme. Offline (cairo + Pillow), no manim/network needed.

Outputs into slide8/:
  1_prompt_chaining.gif   2_routing.gif   3_parallelization.gif
  4_orchestrator_workers.gif   5_evaluator_optimizer.gif
plus a *_still.png representative frame for each (used by the PDF).
"""

import os, io, math, cairo
from PIL import Image

CW, CH = 600, 300                      # canvas
IVORY = (0xF6/255, 0xF1/255, 0xE7/255)
INK   = (0x2B/255, 0x27/255, 0x23/255)
SOFT  = (0x6B/255, 0x63/255, 0x58/255)
CLAY  = (0xCC/255, 0x78/255, 0x5C/255)
EDGE  = (0.74, 0.71, 0.66)
FONT  = "Noto Sans CJK KR"
OUT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slide8")
os.makedirs(OUT, exist_ok=True)

class Node:
    def __init__(self, cx, cy, label, w=76, h=42, kind="box"):
        self.cx, self.cy, self.label, self.w, self.h, self.kind = cx, cy, label, w, h, kind
    @property
    def r(self): return (self.cx + self.w/2, self.cy)
    @property
    def l(self): return (self.cx - self.w/2, self.cy)
    @property
    def c(self): return (self.cx, self.cy)

def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x+w-r, y+r, r, -math.pi/2, 0)
    c.arc(x+w-r, y+h-r, r, 0, math.pi/2)
    c.arc(x+r, y+h-r, r, math.pi/2, math.pi)
    c.arc(x+r, y+r, r, math.pi, 1.5*math.pi)
    c.close_path()

def draw_node(c, n, hot=0.0, fs=15):
    x, y = n.cx - n.w/2, n.cy - n.h/2
    # shadow
    c.set_source_rgba(0, 0, 0, 0.10); rrect(c, x+1.5, y+2.5, n.w, n.h, 10); c.fill()
    # fill (tints toward clay when hot)
    fr = (1-0.12*hot, 1-0.45*hot*0.5, 1-0.55*hot*0.5)
    c.set_source_rgb(*[min(1, v) for v in (1- (1-CLAY[0])*0.10*hot, 1-(1-CLAY[1])*0.10*hot, 1-(1-CLAY[2])*0.10*hot)])
    rrect(c, x, y, n.w, n.h, 10); c.fill()
    # border
    if hot > 0.02:
        c.set_source_rgba(CLAY[0], CLAY[1], CLAY[2], 0.4 + 0.6*hot); c.set_line_width(2.2)
    else:
        c.set_source_rgba(0, 0, 0, 0.16); c.set_line_width(1.2)
    rrect(c, x, y, n.w, n.h, 10); c.stroke()
    # label
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(fs)
    ext = c.text_extents(n.label)
    c.set_source_rgb(*INK)
    c.move_to(n.cx - ext.x_advance/2, n.cy + fs*0.34)
    c.show_text(n.label)

def draw_edge(c, a, b, dashed=False):
    c.set_source_rgba(EDGE[0], EDGE[1], EDGE[2], 1)
    c.set_line_width(2)
    if dashed: c.set_dash([5, 4])
    c.move_to(*a); c.line_to(*b); c.stroke()
    c.set_dash([])
    # arrow head
    ang = math.atan2(b[1]-a[1], b[0]-a[0]); s = 6
    c.move_to(*b)
    c.line_to(b[0]-s*math.cos(ang-0.4), b[1]-s*math.sin(ang-0.4))
    c.line_to(b[0]-s*math.cos(ang+0.4), b[1]-s*math.sin(ang+0.4))
    c.close_path(); c.fill()

def pulse(c, a, b, t, r=6):
    x = a[0] + (b[0]-a[0])*t
    y = a[1] + (b[1]-a[1])*t
    g = cairo.RadialGradient(x, y, 0, x, y, r*2.2)
    g.add_color_stop_rgba(0, CLAY[0], CLAY[1], CLAY[2], 0.95)
    g.add_color_stop_rgba(1, CLAY[0], CLAY[1], CLAY[2], 0)
    c.set_source(g); c.arc(x, y, r*2.2, 0, 2*math.pi); c.fill()
    c.set_source_rgb(*CLAY); c.arc(x, y, r, 0, 2*math.pi); c.fill()

def caption(c, text):
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    c.set_font_size(17)
    ext = c.text_extents(text)
    c.set_source_rgb(*SOFT)
    c.move_to(CW/2 - ext.x_advance/2, 30)
    c.show_text(text)

def new_ctx():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, CW, CH)
    c = cairo.Context(surf)
    c.set_source_rgb(*IVORY); c.paint()
    return surf, c

def surf_to_pil(surf):
    buf = io.BytesIO(); surf.write_to_png(buf); buf.seek(0)
    return Image.open(buf).convert("RGB")

def hot_for(seg_pos, node, path_nodes, idx_active):
    """highlight a node when the pulse is near it"""
    return 0.0

# ---------- pulse helpers along a chain of nodes ----------
def chain_segments(nodes):
    """edges between consecutive nodes (right -> left)."""
    return [(nodes[i].r, nodes[i+1].l) for i in range(len(nodes)-1)]

def node_hot(nodes, active_pair, t):
    """return per-node hotness based on current segment + t."""
    hots = [0.0]*len(nodes)
    i = active_pair
    # ramp: entering node i+1 as t->1, leaving node i as t->0
    hots[i]   = max(hots[i], 1-t)
    hots[i+1] = max(hots[i+1], t)
    return hots

# ===================== pattern builders =====================
def render_gif(name, frame_fn, n_frames=46, dur=70, still_at=0.5, out_dir=OUT):
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    for f in range(n_frames):
        t = f / n_frames
        surf, c = new_ctx()
        frame_fn(c, t)
        frames.append(surf_to_pil(surf))
    still = frames[int(n_frames*still_at)]
    still.save(os.path.join(out_dir, name + "_still.png"))
    frames[0].save(os.path.join(out_dir, name + ".gif"), save_all=True,
                   append_images=frames[1:], duration=dur, loop=0, disposal=2)
    print("wrote", name)

# ---- infinite loop between 방법 1 and 방법 2 (slide 18) ----
def _bez(p0, p1, p2, p3, u):
    mu = 1-u
    return (mu**3*p0[0]+3*mu**2*u*p1[0]+3*mu*u**2*p2[0]+u**3*p3[0],
            mu**3*p0[1]+3*mu**2*u*p1[1]+3*mu*u**2*p2[1]+u**3*p3[1])

def _bez_arrow(c, p3, p2):
    ang = math.atan2(p3[1]-p2[1], p3[0]-p2[0]); s = 9
    c.set_source_rgba(EDGE[0], EDGE[1], EDGE[2], 1)
    c.move_to(*p3)
    c.line_to(p3[0]-s*math.cos(ang-0.45), p3[1]-s*math.sin(ang-0.45))
    c.line_to(p3[0]-s*math.cos(ang+0.45), p3[1]-s*math.sin(ang+0.45))
    c.close_path(); c.fill()

def f_loop(c, t):
    left  = Node(170, 150, "Model", w=156, h=72)
    right = Node(430, 150, "Harness", w=156, h=72)
    # top arc: 방법1 -> 방법2 ; bottom arc: 방법2 -> 방법1
    top = [(left.cx+50, left.cy-36), (left.cx+70, 46),
           (right.cx-70, 46), (right.cx-50, right.cy-36)]
    bot = [(right.cx-50, right.cy+36), (right.cx-70, 254),
           (left.cx+70, 254), (left.cx+50, left.cy+36)]
    # draw arcs
    c.set_source_rgba(*EDGE, 1); c.set_line_width(3)
    for arc in (top, bot):
        c.move_to(*arc[0]); c.curve_to(*arc[1], *arc[2], *arc[3]); c.stroke()
    _bez_arrow(c, top[3], _bez(*top, 0.92))
    _bez_arrow(c, bot[3], _bez(*bot, 0.92))
    # node hotness based on pulse arrival
    h_left = h_right = 0.0
    if t < 0.5:
        u = t/0.5; px, py = _bez(*top, u); h_right = max(0, (u-0.7)/0.3)
        h_left = max(0, (0.3-u)/0.3)
    else:
        u = (t-0.5)/0.5; px, py = _bez(*bot, u); h_left = max(0, (u-0.7)/0.3)
        h_right = max(0, (0.3-u)/0.3)
    draw_node(c, left, h_left, fs=27)
    draw_node(c, right, h_right, fs=27)
    # pulse
    g = cairo.RadialGradient(px, py, 0, px, py, 16)
    g.add_color_stop_rgba(0, *CLAY, 0.95); g.add_color_stop_rgba(1, *CLAY, 0)
    c.set_source(g); c.arc(px, py, 16, 0, 2*math.pi); c.fill()
    c.set_source_rgb(*CLAY); c.arc(px, py, 7, 0, 2*math.pi); c.fill()

# 1. Prompt chaining: In -> LLM1 -> LLM2 -> LLM3 -> Out
def f_chain(c, t):
    caption(c, "1. Prompt Chaining")
    y = 175
    ns = [Node(70, y, "In", w=48), Node(185, y, "LLM 1", w=84),
          Node(300, y, "LLM 2", w=84), Node(415, y, "LLM 3", w=84),
          Node(530, y, "Out", w=48)]
    segs = chain_segments(ns)
    pos = t * len(segs)
    seg_i = min(int(pos), len(segs)-1)
    local = pos - seg_i
    for a, b in segs: draw_edge(c, a, b)
    hots = node_hot(ns, seg_i, local)
    for n, h in zip(ns, hots): draw_node(c, n, h)
    pulse(c, *segs[seg_i], local)

# generic fan pattern: In -> [mid] -> branches -> [merge] -> Out
def fan_frame(c, title, mid_label, merge_label, branch_labels):
    caption(c, title)
    y0 = 178
    nodes = {}
    nodes["in"] = Node(48, y0, "In", w=46)
    if mid_label:
        nodes["mid"] = Node(168, y0, mid_label, w=96)
    bx = 320
    ys = [98, 178, 258]
    branches = [Node(bx, by, lb, w=86) for by, lb in zip(ys, branch_labels)]
    if merge_label:
        nodes["merge"] = Node(470, y0, merge_label, w=112)
        out_x = 558
    else:
        out_x = 470
    nodes["out"] = Node(out_x, y0, "Out", w=46)
    return nodes, branches

def draw_fan(c, nodes, branches, hot_in=0, hot_mid=0, hot_branches=None,
             hot_merge=0, hot_out=0):
    hot_branches = hot_branches or [0,0,0]
    src = nodes.get("mid", nodes["in"])
    # edges in->mid
    if "mid" in nodes: draw_edge(c, nodes["in"].r, nodes["mid"].l)
    # src -> branches
    for b in branches: draw_edge(c, src.r, b.l)
    # branches -> merge/out
    tgt = nodes.get("merge")
    for b in branches:
        draw_edge(c, b.r, (tgt.l if tgt else nodes["out"].l))
    if "merge" in nodes: draw_edge(c, nodes["merge"].r, nodes["out"].l)
    # nodes
    draw_node(c, nodes["in"], hot_in)
    if "mid" in nodes: draw_node(c, nodes["mid"], hot_mid)
    for b, h in zip(branches, hot_branches): draw_node(c, b, h)
    if "merge" in nodes: draw_node(c, nodes["merge"], hot_merge)
    draw_node(c, nodes["out"], hot_out)

# 2. Routing: In -> Router -> one branch -> Out
def f_routing(c, t):
    nodes, branches = fan_frame(c, "2. Routing", "Router", None,
                                ["LLM A", "LLM B", "LLM C"])
    sel = int(t * 3) % 3            # which branch this cycle
    local3 = (t * 3) % 1
    hb = [0,0,0]
    src = nodes["mid"]
    draw_fan(c, nodes, branches,
             hot_in=max(0,1-local3*2) if False else 0,
             hot_mid=1-local3, hot_branches=None, hot_out=0)
    # active pulse: in->router (first third of local), router->branch, branch->out
    if local3 < 0.4:
        tt = local3/0.4
        pulse(c, nodes["in"].r, nodes["mid"].l, tt)
    elif local3 < 0.7:
        tt = (local3-0.4)/0.3
        pulse(c, src.r, branches[sel].l, tt)
    else:
        tt = (local3-0.7)/0.3
        pulse(c, branches[sel].r, nodes["out"].l, tt)
    draw_node(c, branches[sel], 0.9)

# 3. Parallelization: In -> 3 branches at once -> Aggregator -> Out
def f_parallel(c, t):
    nodes, branches = fan_frame(c, "3. Parallelization", None, "Aggregator",
                                ["LLM 1", "LLM 2", "LLM 3"])
    draw_fan(c, nodes, branches)
    if t < 0.5:
        tt = t/0.5
        for b in branches: pulse(c, nodes["in"].r, b.l, tt)
        for b in branches: draw_node(c, b, tt)
    else:
        tt = (t-0.5)/0.5
        for b in branches:
            pulse(c, b.r, nodes["merge"].l, tt)
            draw_node(c, b, 1-tt)
        draw_node(c, nodes["merge"], tt)

# 4. Orchestrator-workers: In -> Orchestrator -> workers -> Synthesizer -> Out
def f_orch(c, t):
    nodes, branches = fan_frame(c, "4. Orchestrator–Workers", "Orchestr.",
                                "Synthesizer", ["Worker", "Worker", "Worker"])
    draw_fan(c, nodes, branches)
    if t < 0.33:
        pulse(c, nodes["in"].r, nodes["mid"].l, t/0.33)
        draw_node(c, nodes["mid"], t/0.33)
    elif t < 0.66:
        tt = (t-0.33)/0.33
        for b in branches:
            pulse(c, nodes["mid"].r, b.l, tt); draw_node(c, b, tt)
        draw_node(c, nodes["mid"], 1)
    else:
        tt = (t-0.66)/0.34
        for b in branches:
            pulse(c, b.r, nodes["merge"].l, tt); draw_node(c, b, 1-tt)
        draw_node(c, nodes["merge"], tt)

# 5. Evaluator-optimizer: In -> Generator <-> Evaluator (loop) -> Out
def f_eval(c, t):
    caption(c, "5. Evaluator–Optimizer")
    y = 185
    nin = Node(50, y, "In", w=46)
    gen = Node(190, y, "Generator", w=110)
    ev  = Node(370, y, "Evaluator", w=110)
    out = Node(545, y, "Out", w=46)
    draw_edge(c, nin.r, gen.l)
    draw_edge(c, gen.r, ev.l)
    draw_edge(c, ev.r, out.l)
    # feedback loop (Evaluator -> Generator) curved above, dashed
    c.set_source_rgba(*CLAY, 0.7); c.set_line_width(2); c.set_dash([5,4])
    c.move_to(ev.cx, ev.cy - ev.h/2)
    c.curve_to(ev.cx, y-78, gen.cx, y-78, gen.cx, gen.cy - gen.h/2)
    c.stroke(); c.set_dash([])
    # arrow into generator top
    c.set_source_rgba(*CLAY, 0.9)
    ax, ay = gen.cx, gen.cy - gen.h/2
    c.move_to(ax, ay); c.line_to(ax-5, ay-8); c.line_to(ax+5, ay-8); c.close_path(); c.fill()
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(12)
    c.set_source_rgb(*SOFT); lbl="feedback"; e=c.text_extents(lbl)
    c.move_to((gen.cx+ev.cx)/2 - e.x_advance/2, y-84); c.show_text(lbl)

    phase = t
    h_in = h_gen = h_ev = h_out = 0.0
    pulse_call = None
    if phase < 0.2:
        tt = phase/0.2; h_in = 1
        pulse_call = ("line", nin.r, gen.l, tt)
    elif phase < 0.45:
        tt = (phase-0.2)/0.25; h_gen = 1
        pulse_call = ("line", gen.r, ev.l, tt)
    elif phase < 0.7:
        tt = (phase-0.45)/0.25; h_ev = 1; h_gen = 0.5
        pulse_call = ("bez", tt)
    elif phase < 0.85:
        tt = (phase-0.7)/0.15; h_gen = 1
        pulse_call = ("line", gen.r, ev.l, tt)
    else:
        tt = (phase-0.85)/0.15; h_ev = 1; h_out = tt
        pulse_call = ("line", ev.r, out.l, tt)
    # nodes first
    draw_node(c, nin, h_in); draw_node(c, gen, h_gen)
    draw_node(c, ev, h_ev); draw_node(c, out, h_out)
    # pulse on top
    if pulse_call[0] == "line":
        pulse(c, pulse_call[1], pulse_call[2], pulse_call[3])
    else:
        u = pulse_call[1]
        def bez(p0,p1,p2,p3,uu):
            mu=1-uu
            return (mu**3*p0[0]+3*mu**2*uu*p1[0]+3*mu*uu**2*p2[0]+uu**3*p3[0],
                    mu**3*p0[1]+3*mu**2*uu*p1[1]+3*mu*uu**2*p2[1]+uu**3*p3[1])
        p0=(ev.cx,ev.cy-ev.h/2);p1=(ev.cx,y-78);p2=(gen.cx,y-78);p3=(gen.cx,gen.cy-gen.h/2)
        bx,by=bez(p0,p1,p2,p3,u)
        c.set_source_rgb(*CLAY); c.arc(bx,by,6,0,2*math.pi); c.fill()

if __name__ == "__main__":
    render_gif("1_prompt_chaining", f_chain)
    render_gif("2_routing", f_routing, n_frames=60)
    render_gif("3_parallelization", f_parallel)
    render_gif("4_orchestrator_workers", f_orch, n_frames=54)
    render_gif("5_evaluator_optimizer", f_eval, n_frames=60)
    render_gif("loop", f_loop, n_frames=64, dur=55,
               out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "slide18"))
    print("done")
