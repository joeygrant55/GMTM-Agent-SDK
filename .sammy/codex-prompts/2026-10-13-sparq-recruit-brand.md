# Codex brief: SPARQ Recruit brand lockup (design only)

From Fable for Joey, 2026-10-13. Joey's ask: a more professional SPARQ Recruit identity, made by Codex.
Fable integrates the files into the app after Joey approves; Codex does not edit the app code.

## What SPARQ Recruit is
A free recruiting helper inside GMTM for high-school girls (13-17) in flag football: matched women's college
programs, current roster make-up, and a coach email kit (the athlete sends from her own email). It builds on
SPARQ, GMTM's in-person combine and testing brand. Live: https://sparq.gmtm.com (sign-in via GMTM).

## Deliverables
1. Lockup: the existing SPARQ wordmark + "Recruit". Horizontal. SVG (outlined, real type, no raster text) and
   transparent PNG @1x/@2x/@3x.
2. Versions: white on dark (primary), black on light.
3. Small mark/favicon: SVG + 32/180/512 PNG (works at 16 px).
4. Share image (Open Graph) 1200x630 PNG for sparq.gmtm.com links.
5. Optional: email header 600x120 PNG for the athlete invite email.

## Constraints (measured in the live app)
- SPARQ wordmark source: frontend/public/sparq-wordmark.png in joeygrant55/GMTM-Agent-SDK (branch
  feat/junior-pilot), 3266x547, black on transparent; the app shows it white (CSS invert). Do not redraw it.
- App colors: background #0B0B0C, raised #131316/#1C1C20, lines #222226, text #F4F4F5, accent lime #CAFD00.
  Font in the app: Space Grotesk.
- Header sizes: lockup must read at 84 px wide total height ~14 px on phones and ~128-200 px wide on desktop.
  At 360 px phone width the header has room for about 150 px of lockup.
- Audience is teens and parents: clean, athletic, credible. No mascots. Avoid the word "Agent".
- Text must be crisp and correct; image models garble letters, so final type must be vector.

## Hand-back
Put files in a folder and tell Fable the path. Include a one-line note on font and any license.
