# Frontend-Only GitHub Pages Layout

Use this layout when only `frontend/` is deployed to GitHub Pages.

## Directory
```text
frontend/
  index.html
  app.js
  config.js
  styles.css
  faces/
    neutral.png
    happy.png
    sad.png
    angry.png
    crying.png
    smiling.png
    smirk.png
    shy_smile.png
    blushing.png
    teary.png
    surprised.png
    confused.png
    annoyed.png
    pouting.png
    tired.png
    scared.png
    excited.png
```

## Path Rules
- Base portraits: `./faces/{face_slug}.png`
- `face_slug`: lowercase + spaces replaced by `_`
- Example: `shy smile` -> `shy_smile.png`

## config.js
- `window.NPC_API_BASE_URL`: backend public URL
- `window.NPC_FACE_ASSET_BASE_URL`: keep `./faces`
- `window.NPC_FACE_EXT`: usually `png`

## Runtime Behavior
- Every chat turn: show local base portrait from `frontend/faces`.
- If backend returns generated image or queued status:
  - queued: poll `/api/image/status`
  - generated: overlay generated image URL on top of base
