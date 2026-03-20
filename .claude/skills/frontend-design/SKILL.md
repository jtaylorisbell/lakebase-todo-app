---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
---

This skill guides creation of distinctive, production-grade frontend interfaces. Implement real working code with exceptional attention to aesthetic details and creative choices.

## Databricks Brand Guidelines

This is a Databricks template app. All frontend work MUST follow the official Databricks brand.

### Typography
- **Primary font**: `DM Sans` (weights: 400 regular, 500 medium, 700 bold) — use for all UI text, headings, labels
- **Monospace font**: `DM Mono` (weights: 400, 500) — use exclusively for code, metadata, timestamps, tags, counts
- Load both via Google Fonts: `https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap`
- NEVER use Inter, Roboto, Arial, Space Grotesk, Syne, or any other font family

### Colors
Always use the official Databricks palette. Reference: https://brandguides.brandfolder.com/databricks-extended-brand-guidelines/colors

**Primary**
- Lava 600 `#FF3621` — primary brand accent (CTAs, highlights, active states, progress)
- Navy 800 `#1B3139` — primary dark background / surface
- Oat Medium `#EEEDE9` — primary text on dark backgrounds
- Oat Light `#F9F7F4` — backgrounds on light themes

**Navy family** (dark UI backgrounds)
- Navy 900 `#0B2026` — deepest background
- Navy 800 `#1B3139` — surface
- Navy 700 `#143D4A` — elevated surface
- Navy 600 `#1B5162` — borders
- Navy 500 `#618794` — muted text / bright borders
- Navy 400 `#90A5B1` — secondary text

**Semantic**
- Success / low priority: Green 600 `#00A972`
- Warning / medium priority: Yellow 600 `#FFAB00`
- Danger / high priority: Maroon 600 `#98102A`
- Navigation gray: `#303F47`
- Text gray: `#5A6F77`
- Lines gray: `#DCE0E2`

**Extended palette** (use sparingly for accents)
- Lava 500 `#FF5F46`, Lava 400 `#FF9E94`
- Blue 600 `#2272B4`, Blue 500 `#4299E0`

#### Required Footer
Every frontend MUST include a "Powered by Databricks Apps" footer with the official Databricks logo. Use this exact implementation in the sidebar or bottom of the page:

```tsx
<div className="sidebar-footer">
  <img
    src="https://cdn.bfldr.com/9AYANS2F/at/k8bgnnxhb4bggjk88r4x9snf/databricks-symbol-color.svg?auto=webp&format=png"
    alt="Databricks"
    className="footer-logo"
  />
  <span className="footer-text">Powered by Databricks Apps</span>
</div>
```

```css
.sidebar-footer {
  padding: 14px 24px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.footer-logo { width: 16px; height: 16px; object-fit: contain; flex-shrink: 0; }
.footer-text { font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); letter-spacing: 0.03em; white-space: nowrap; }
```

## Design Principles
- Dark theme preferred: Navy 900 background with Oat Medium text and Lava 600 accent
- Sidebar layouts work well for data-dense apps
- Use DM Mono for all numeric data, tags, timestamps, and code-like content
- Use Lava 600 sparingly as a true accent — don't overuse it
- Noise/grain textures and subtle border treatments fit the Databricks engineering aesthetic

## Design Thinking

Before coding, understand the context and commit to a clear aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Databricks apps should feel professional, engineering-grade, and precise — not playful or decorative
- **Constraints**: Technical requirements (framework, performance, accessibility)
- **Differentiation**: What makes this memorable within the Databricks aesthetic?

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually cohesive with the Databricks brand
- Meticulously refined in spacing, hierarchy, and interaction details

## Frontend Implementation Guidelines

- **Motion**: CSS animations for entrance effects and micro-interactions. Staggered reveals on load. Subtle hover states.
- **Spatial Composition**: Clean grid layouts. Generous but not wasteful whitespace. Clear typographic hierarchy.
- **Backgrounds**: Noise texture overlays (3–5% opacity) add depth. Subtle border treatments over heavy shadows.
- **Scrollbars**: Style to match theme (thin, muted color).

NEVER use generic AI-generated aesthetics: purple gradients, cookie-cutter card layouts, or fonts outside the Databricks brand stack.
