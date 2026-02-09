# SPARQ Demo Video Pipeline — Research (Feb 9, 2026)

## Options Evaluated

### 1. Remotion (Recommended ✅)
- **What:** React-based programmatic video generation
- **How:** Write video scenes as React components → render to MP4
- **Pros:**
  - Full React ecosystem (reuse existing SPARQ components!)
  - Pixel-perfect control over every frame
  - Works with existing Node.js stack
  - Claude Code integration documented
  - Free for self-rendering, paid cloud rendering available
  - Can animate data, charts, UI mockups natively
- **Cons:**
  - Rendering takes compute (can be slow locally)
  - Learning curve for timeline/animation APIs
- **Best for:** Product demo videos showing the SPARQ UI in action with animated data

### 2. fal.ai
- **What:** AI video generation API (text-to-video, image-to-video)
- **Pros:**
  - AI-generated cinematic footage
  - Good for marketing sizzle reels
- **Cons:**
  - Less control over exact UI/product shots
  - API costs per generation
  - AI video still has artifacts
- **Best for:** Marketing b-roll, not product demos

## Recommendation

**Use Remotion for SPARQ demo video.** Reasons:
1. We already have React components from the demo page
2. Can animate real athlete data flowing through the platform
3. Pixel-perfect product shots > AI-generated approximations
4. One-time setup, then generate updated videos anytime

### Suggested Demo Video Structure (60s)
1. **0-5s:** SPARQ logo + tagline animation
2. **5-20s:** Athlete profile card populating with real data
3. **20-35s:** Agent analyzing → college matches appearing
4. **35-50s:** Side-by-side: manual recruiting vs SPARQ agent speed
5. **50-60s:** CTA + pricing/signup

### Next Steps
1. `npx create-video@latest` in sparq-agent/video/
2. Port key React components (athlete card, dashboard)
3. Add spring animations for data flow
4. Render locally or use Remotion Lambda for cloud rendering

---

*Research by Sammy — ready for Joey's review before building*
