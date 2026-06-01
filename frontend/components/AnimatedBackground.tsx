"use client";

import { useEffect, useRef } from "react";

/**
 * Animated background — academic manuscript meets a 3D data globe.
 *
 * Layers (back → front):
 *  1. Subtle grid (graph paper feel)
 *  2. Drifting starfield particles
 *  3. Rotating 3D wireframe globe
 *      - latitude / longitude wireframe
 *      - ~600 dot nodes on the sphere surface (data points)
 *      - faint connection arcs between nearby visible nodes (peer-review streams)
 *      - rim glow + soft yellow ambient
 *  4. Glow orbs (ambient yellow light)
 *  5. Vignette top/bottom for legibility
 *
 * Pure canvas, zero dependencies. Honors prefers-reduced-motion.
 */
export function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvasEl: HTMLCanvasElement | null = canvasRef.current;
    if (!canvasEl) return;
    const ctxMaybe = canvasEl.getContext("2d", { alpha: true });
    if (!ctxMaybe) return;
    const canvas: HTMLCanvasElement = canvasEl;
    const ctx: CanvasRenderingContext2D = ctxMaybe;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    /* ── State ─────────────────────────────────────────────────────────── */
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let width = 0;
    let height = 0;
    let cx = 0;
    let cy = 0;
    let radius = 0;
    let mx = 0; // mouse X normalized -1..1
    let my = 0;
    let pointerInfluence = 0;
    let raf = 0;
    let last = performance.now();
    let yaw = 0;
    let pitch = -0.3; // slight tilt

    /* ── Geometry: fibonacci-distributed nodes on a unit sphere ───────── */
    const NODE_COUNT = 620;
    const nodes = new Float32Array(NODE_COUNT * 3);
    {
      const golden = Math.PI * (3 - Math.sqrt(5));
      for (let i = 0; i < NODE_COUNT; i++) {
        const y = 1 - (i / (NODE_COUNT - 1)) * 2;
        const r = Math.sqrt(1 - y * y);
        const theta = golden * i;
        nodes[i * 3] = Math.cos(theta) * r;
        nodes[i * 3 + 1] = y;
        nodes[i * 3 + 2] = Math.sin(theta) * r;
      }
    }

    /* ── Latitude / longitude wireframe samples ───────────────────────── */
    type RingSegment = { points: [number, number, number][]; type: "lat" | "lon" };
    const rings: RingSegment[] = [];
    {
      const segs = 96;
      // latitude rings
      for (let i = 1; i < 8; i++) {
        const phi = (i / 8) * Math.PI - Math.PI / 2; // -π/2..π/2
        const cosp = Math.cos(phi);
        const y = Math.sin(phi);
        const pts: [number, number, number][] = [];
        for (let j = 0; j <= segs; j++) {
          const t = (j / segs) * Math.PI * 2;
          pts.push([Math.cos(t) * cosp, y, Math.sin(t) * cosp]);
        }
        rings.push({ points: pts, type: "lat" });
      }
      // longitude rings (meridians)
      for (let i = 0; i < 12; i++) {
        const lon = (i / 12) * Math.PI * 2;
        const cosl = Math.cos(lon);
        const sinl = Math.sin(lon);
        const pts: [number, number, number][] = [];
        for (let j = 0; j <= segs; j++) {
          const phi = (j / segs) * Math.PI - Math.PI / 2;
          const cosp = Math.cos(phi);
          pts.push([cosl * cosp, Math.sin(phi), sinl * cosp]);
        }
        rings.push({ points: pts, type: "lon" });
      }
    }

    /* ── Background starfield (depth-parallax dots) ───────────────────── */
    const STAR_COUNT = 80;
    const stars = Array.from({ length: STAR_COUNT }, () => ({
      x: Math.random() * 2 - 1,
      y: Math.random() * 2 - 1,
      z: Math.random() * 0.6 + 0.2,
      r: Math.random() * 1.2 + 0.3,
      tw: Math.random() * Math.PI * 2,
      twSpeed: Math.random() * 0.6 + 0.2,
    }));

    /* ── "Data pulse" arcs — random curved lines that fade in/out ──── */
    type Pulse = {
      a: number; // node index A
      b: number; // node index B
      t: number; // 0..1 lifetime progress
      life: number; // total life in seconds
    };
    const pulses: Pulse[] = [];
    const MAX_PULSES = 14;

    function spawnPulse() {
      const a = Math.floor(Math.random() * NODE_COUNT);
      let b = Math.floor(Math.random() * NODE_COUNT);
      // prefer "distant" pairs for nicer arcs
      let tries = 0;
      while (tries++ < 4) {
        const ax = nodes[a * 3];
        const ay = nodes[a * 3 + 1];
        const az = nodes[a * 3 + 2];
        const bx = nodes[b * 3];
        const by = nodes[b * 3 + 1];
        const bz = nodes[b * 3 + 2];
        const d = (ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2;
        if (d > 1.6) break;
        b = Math.floor(Math.random() * NODE_COUNT);
      }
      pulses.push({ a, b, t: 0, life: 1.6 + Math.random() * 1.6 });
    }

    /* ── Resize handling ──────────────────────────────────────────────── */
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Center the globe slightly right of the hero copy on wide screens
      cx = width >= 1024 ? width * 0.78 : width * 0.5;
      cy = width >= 1024 ? height * 0.5 : height * 0.42;
      radius = Math.min(width, height) * (width >= 1024 ? 0.36 : 0.45);
    }
    resize();
    window.addEventListener("resize", resize);

    /* ── Mouse parallax ───────────────────────────────────────────────── */
    function onMove(e: MouseEvent) {
      mx = (e.clientX / window.innerWidth) * 2 - 1;
      my = (e.clientY / window.innerHeight) * 2 - 1;
      pointerInfluence = Math.min(1, pointerInfluence + 0.02);
    }
    window.addEventListener("mousemove", onMove);

    /* ── Helpers ──────────────────────────────────────────────────────── */
    function project(
      x: number,
      y: number,
      z: number,
      sinY: number,
      cosY: number,
      sinP: number,
      cosP: number
    ) {
      // Rotate around Y (yaw)
      const x1 = x * cosY + z * sinY;
      const z1 = -x * sinY + z * cosY;
      // Rotate around X (pitch)
      const y2 = y * cosP - z1 * sinP;
      const z2 = y * sinP + z1 * cosP;
      // Perspective project
      const persp = 2.4;
      const scale = persp / (persp - z2);
      return {
        sx: cx + x1 * radius * scale,
        sy: cy + y2 * radius * scale,
        depth: z2, // -1 (back) .. 1 (front)
        scale,
      };
    }

    /* ── Main loop ────────────────────────────────────────────────────── */
    function frame(now: number) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      // gentle pointer influence decay
      pointerInfluence *= 0.985;

      if (!reduceMotion) {
        yaw += dt * 0.18 + mx * pointerInfluence * 0.0008;
        pitch = -0.3 + my * pointerInfluence * 0.18;
      }

      const sinY = Math.sin(yaw);
      const cosY = Math.cos(yaw);
      const sinP = Math.sin(pitch);
      const cosP = Math.cos(pitch);

      ctx.clearRect(0, 0, width, height);

      /* — Starfield — */
      for (const s of stars) {
        s.tw += dt * s.twSpeed;
        const tw = 0.4 + Math.sin(s.tw) * 0.4;
        const sx = (s.x * 0.5 + 0.5) * width;
        const sy = (s.y * 0.5 + 0.5) * height;
        ctx.beginPath();
        ctx.fillStyle = `rgba(250, 204, 21, ${0.06 * tw + 0.04})`;
        ctx.arc(sx, sy, s.r, 0, Math.PI * 2);
        ctx.fill();
      }

      /* — Outer rim glow — */
      const rimGrad = ctx.createRadialGradient(cx, cy, radius * 0.85, cx, cy, radius * 1.35);
      rimGrad.addColorStop(0, "rgba(250, 204, 21, 0.0)");
      rimGrad.addColorStop(0.55, "rgba(250, 204, 21, 0.05)");
      rimGrad.addColorStop(1, "rgba(250, 204, 21, 0)");
      ctx.fillStyle = rimGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.35, 0, Math.PI * 2);
      ctx.fill();

      /* — Inner sphere shadow disk (gives mass) — */
      const innerShade = ctx.createRadialGradient(
        cx - radius * 0.3,
        cy - radius * 0.3,
        radius * 0.1,
        cx,
        cy,
        radius
      );
      innerShade.addColorStop(0, "rgba(20, 20, 24, 0.0)");
      innerShade.addColorStop(0.7, "rgba(0, 0, 0, 0.25)");
      innerShade.addColorStop(1, "rgba(0, 0, 0, 0.55)");
      ctx.fillStyle = innerShade;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      /* — Wireframe lat/lon rings — */
      for (const ring of rings) {
        ctx.beginPath();
        let started = false;
        for (let i = 0; i < ring.points.length; i++) {
          const p = ring.points[i];
          const pr = project(p[0], p[1], p[2], sinY, cosY, sinP, cosP);
          if (pr.depth < -0.05) {
            // hidden behind the sphere — break the line
            started = false;
            continue;
          }
          if (!started) {
            ctx.moveTo(pr.sx, pr.sy);
            started = true;
          } else {
            ctx.lineTo(pr.sx, pr.sy);
          }
        }
        const alpha = ring.type === "lat" ? 0.07 : 0.09;
        ctx.strokeStyle = `rgba(250, 204, 21, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      /* — Surface dot nodes — */
      // Pre-project all nodes once for reuse with arcs
      const projected = new Float32Array(NODE_COUNT * 4); // sx, sy, depth, scale
      for (let i = 0; i < NODE_COUNT; i++) {
        const x = nodes[i * 3];
        const y = nodes[i * 3 + 1];
        const z = nodes[i * 3 + 2];
        const pr = project(x, y, z, sinY, cosY, sinP, cosP);
        projected[i * 4] = pr.sx;
        projected[i * 4 + 1] = pr.sy;
        projected[i * 4 + 2] = pr.depth;
        projected[i * 4 + 3] = pr.scale;
      }

      for (let i = 0; i < NODE_COUNT; i++) {
        const depth = projected[i * 4 + 2];
        if (depth < -0.05) continue; // back-face cull
        const sx = projected[i * 4];
        const sy = projected[i * 4 + 1];
        const scale = projected[i * 4 + 3];
        const front = (depth + 1) * 0.5; // 0..1
        // a sparse subset glows yellow; the rest white
        const isHot = (i * 31) % 17 === 0;
        const r = (isHot ? 1.6 : 1.1) * scale;
        const alpha = 0.25 + front * 0.65;
        if (isHot) {
          ctx.fillStyle = `rgba(253, 224, 71, ${alpha})`;
          ctx.shadowColor = "rgba(250, 204, 21, 0.55)";
          ctx.shadowBlur = 8;
        } else {
          ctx.fillStyle = `rgba(245, 245, 244, ${alpha * 0.7})`;
          ctx.shadowBlur = 0;
        }
        ctx.beginPath();
        ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.shadowBlur = 0;

      /* — Pulse arcs — */
      if (!reduceMotion && pulses.length < MAX_PULSES && Math.random() < 0.06) {
        spawnPulse();
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.t += dt / p.life;
        if (p.t >= 1) {
          pulses.splice(i, 1);
          continue;
        }

        const ax = projected[p.a * 4];
        const ay = projected[p.a * 4 + 1];
        const ad = projected[p.a * 4 + 2];
        const bx = projected[p.b * 4];
        const by = projected[p.b * 4 + 1];
        const bd = projected[p.b * 4 + 2];

        // skip if both endpoints behind globe
        if (ad < -0.05 && bd < -0.05) continue;

        // bow the arc up away from the globe center
        const midx = (ax + bx) * 0.5;
        const midy = (ay + by) * 0.5;
        const lift = Math.hypot(ax - bx, ay - by) * 0.35;
        // direction away from globe center
        const dxC = midx - cx;
        const dyC = midy - cy;
        const lenC = Math.hypot(dxC, dyC) || 1;
        const ctrlX = midx + (dxC / lenC) * lift;
        const ctrlY = midy + (dyC / lenC) * lift;

        // ease-in-out fade
        const fade = Math.sin(p.t * Math.PI);
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.quadraticCurveTo(ctrlX, ctrlY, bx, by);
        ctx.strokeStyle = `rgba(250, 204, 21, ${0.35 * fade})`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // travelling head dot along the quadratic bezier
        const tt = p.t;
        const oneT = 1 - tt;
        const hx = oneT * oneT * ax + 2 * oneT * tt * ctrlX + tt * tt * bx;
        const hy = oneT * oneT * ay + 2 * oneT * tt * ctrlY + tt * tt * by;
        ctx.fillStyle = `rgba(253, 224, 71, ${0.9 * fade})`;
        ctx.shadowColor = "rgba(250, 204, 21, 0.9)";
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.arc(hx, hy, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      /* — Soft front sheen highlight — */
      const sheen = ctx.createRadialGradient(
        cx - radius * 0.35,
        cy - radius * 0.4,
        radius * 0.05,
        cx - radius * 0.35,
        cy - radius * 0.4,
        radius * 0.6
      );
      sheen.addColorStop(0, "rgba(250, 204, 21, 0.12)");
      sheen.addColorStop(1, "rgba(250, 204, 21, 0)");
      ctx.fillStyle = sheen;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      raf = requestAnimationFrame(frame);
    }

    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
    };
  }, []);

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
      {/* Deep base — warm graphite, not pure black */}
      <div className="absolute inset-0 bg-[#08080b]" />

      {/* Aurora mesh — slow drifting color blobs across the whole page */}
      <div className="absolute inset-0 aurora-layer">
        <div className="aurora aurora-1" />
        <div className="aurora aurora-2" />
        <div className="aurora aurora-3" />
        <div className="aurora aurora-4" />
      </div>

      {/* Conic spotlight that rotates slowly behind everything */}
      <div className="absolute inset-0 conic-spotlight" />

      {/* Base grid (graph paper feel) */}
      <div className="absolute inset-0 bg-grid bg-mask opacity-70" />

      {/* 3D globe canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        aria-hidden
      />

      {/* Ambient yellow glow orbs */}
      <div
        className="glow-orb animate-float-slow"
        style={{
          width: "640px",
          height: "640px",
          top: "-220px",
          left: "-180px",
          animationDuration: "14s",
        }}
      />
      <div
        className="glow-orb animate-float"
        style={{
          width: "520px",
          height: "520px",
          bottom: "-160px",
          right: "-120px",
          animationDuration: "18s",
          animationDelay: "2s",
        }}
      />

      {/* Paper grain — extremely subtle, kills the "flat black" feel */}
      <div className="absolute inset-0 paper-grain" />

      {/* Soft top fade behind the navbar */}
      <div className="absolute top-0 left-0 right-0 h-40 bg-gradient-to-b from-[#08080b] via-[#08080b]/60 to-transparent" />
      {/* Bottom fade into footer */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-[#08080b] to-transparent" />
      {/* Left fade so hero copy stays readable on top of the globe */}
      <div className="absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-[#08080b]/85 via-[#08080b]/30 to-transparent hidden lg:block" />

      {/* Edge vignette for cinematic framing */}
      <div className="absolute inset-0 edge-vignette" />
    </div>
  );
}
