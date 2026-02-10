# SPARQ Recruiting Video

Remotion-powered athlete recruiting video generator.

## Quick Start

```bash
npm install
npx remotion studio   # Opens browser preview
```

## Render

```bash
# Landscape (1920x1080)
npm run render

# Portrait for social (1080x1920)
npm run render:portrait
```

## Customizing

Edit `src/sample-data.ts` or pass a different `AthleteData` props object.

The `AthleteData` interface accepts: name, sport, position, classYear, location, height, weight, fortyYard, stats array, sparqRating, sparqPercentile, matches array, and optional socialHandles.

## Scenes

| Scene | Frames | Time | Content |
|-------|--------|------|---------|
| Intro | 0-89 | 0-3s | SPARQ logo + tagline |
| Profile | 90-329 | 3-11s | Athlete stats |
| Rating | 330-479 | 11-16s | SPARQ score reveal |
| Matches | 480-779 | 16-26s | College match cards |
| CTA | 780-899 | 26-30s | Call to action |
