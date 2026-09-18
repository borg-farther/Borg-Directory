---
version: alpha
name: Borg Control Room
description: Truth-first dark-mode design system for Borg docs, proof dashboards, and agent-facing landing pages.
colors:
  primary: "#0D1117"
  secondary: "#8B949E"
  tertiary: "#58A6FF"
  tertiary-hover: "#79B8FF"
  neutral: "#161B22"
  surface-2: "#21262D"
  border: "#30363D"
  text-high: "#E6EDF3"
  on-tertiary: "#0D1117"
  success: "#3FB950"
  danger: "#F85149"
  warning: "#D29922"
  violet: "#A371F7"
typography:
  h1:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
    fontSize: 3rem
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  h2:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
    fontSize: 1.75rem
    fontWeight: 700
    lineHeight: 1.2
  body-md:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
    fontSize: 1rem
    lineHeight: 1.6
  body-sm:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
    fontSize: 0.875rem
    lineHeight: 1.5
  label-caps:
    fontFamily: "Segoe UI, -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
    fontSize: 0.75rem
    fontWeight: 600
    letterSpacing: "0.08em"
  code-sm:
    fontFamily: "SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace"
    fontSize: 0.8125rem
    lineHeight: 1.7
rounded:
  sm: 4px
  md: 8px
  lg: 10px
  xl: 12px
  pill: 20px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 40px
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.md}"
    padding: 12px
  button-primary-hover:
    backgroundColor: "{colors.tertiary-hover}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.md}"
    padding: 12px
  button-secondary:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text-high}"
    rounded: "{rounded.md}"
    padding: 12px
  hero-badge:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.secondary}"
    rounded: "{rounded.pill}"
    padding: 4px
  card:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.text-high}"
    rounded: "{rounded.xl}"
    padding: 24px
  code-block:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-high}"
    rounded: "{rounded.md}"
    padding: 16px
  status-success:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.success}"
    rounded: "{rounded.sm}"
    padding: 4px
  status-danger:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.danger}"
    rounded: "{rounded.sm}"
    padding: 4px
  status-warning:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.warning}"
    rounded: "{rounded.sm}"
    padding: 4px
  headline-accent:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.violet}"
    rounded: "{rounded.sm}"
    padding: 4px
  rule-chip:
    backgroundColor: "{colors.border}"
    textColor: "{colors.text-high}"
    rounded: "{rounded.sm}"
    padding: 4px
---

## Overview

Borg should look like a calm operations console, not a glossy marketing splash
page. The product promise is practical: stop wasting time and tokens on dead
ends, surface confidence honestly, and keep evidence in view. The visual system
should feel closer to GitHub-dark, incident tooling, and developer consoles than
consumer SaaS gradients and glassmorphism.

The mood is restrained, technical, and high-signal. Blue marks actionable paths.
Green and red are reserved for outcome states and should never become decorative
brand wallpaper. The only ornamental flourish is the blue→violet headline
highlight used sparingly on landing surfaces.

## Colors

- **Primary ({colors.primary}):** Page background and deepest console surface.
  This is the dominant field color.
- **Neutral ({colors.neutral}):** Main card and panel surface. Use for grouped
  content that should stand off from the page background without looking lifted.
- **Surface-2 ({colors.surface-2}):** Secondary controls, chips, badges, and
  hover states.
- **Text-high ({colors.text-high}):** Primary reading color on dark surfaces.
- **Secondary ({colors.secondary}):** Metadata, captions, muted labels, and
  supporting copy.
- **Tertiary ({colors.tertiary}):** The interaction driver. Links, primary
  buttons, active toggles, and selected states use this blue.
- **Success ({colors.success}):** Positive outcomes, verified wins, and safe GO
  signals. Use only where an outcome meaning exists.
- **Danger ({colors.danger}):** Failures, blocked states, and hard stop cues.
- **Warning ({colors.warning}):** Caution, caveats, and non-fatal risk.
- **Violet ({colors.violet}):** Accent partner for the hero gradient only. Do
  not use as a second independent CTA color.

## Typography

Use the host system sans stack everywhere for interface text. Hierarchy comes
from weight, size, and spacing, not from mixing decorative fonts. Headlines are
compact and heavy; body text stays airy and readable. Code and shell examples
switch to the monospace stack only inside code blocks or inline technical data.

Small uppercase labels are allowed for section markers, status labels, and
before/after comparisons, but they should remain quiet and secondary.

## Layout

The layout should breathe, but not feel sparse. Use `md`/`lg` spacing inside
components, `xl` for section gaps, and `xxl` only for hero-scale separation.
Content containers should stay narrow enough for focused reading: documentation,
proof dashboards, and install flows work best when they feel like a technical
brief, not a magazine spread.

Alignment should be clean and grid-like. Prefer vertical rhythm and predictable
section padding over clever asymmetry.

## Elevation & Depth

Borg surfaces are mostly flat. Separation comes from contrast and borders, not
from heavy shadows. Cards and panels should read as bordered containers on a
shared dark canvas. If depth is used at all, keep it minimal and reserve it for
interactive emphasis or modal interruption.

## Shapes

Corners are modest and functional. `sm` and `md` radii are the defaults for
controls and code affordances. Cards can use `lg` or `xl` to feel slightly more
composed without becoming soft. Pills are reserved for badges, small state
labels, and compact filters.

Avoid large bubbly radii or overly rounded consumer-app styling.

## Components

- `button-primary` is the only high-emphasis action on a screen or card.
- `button-secondary` is for supporting actions, never for the main path.
- `hero-badge` introduces context quietly before the headline.
- `card` is the default grouping surface for installs, proof summaries, and
  pack descriptions.
- `code-block` should feel like part of the console environment: dark, compact,
  and easy to scan/copy.

When a screen shows success/failure comparison, use the shared card surface and
let border or label treatment communicate the outcome state; do not create a
separate unrelated visual language for comparisons.

## Do's and Don'ts

- **Do** keep the interface dark, restrained, and developer-native.
- **Do** use token references in components instead of repeating hex values.
- **Do** reserve green/red/yellow for semantic state, not generic decoration.
- **Do** keep the blue→violet gradient limited to occasional headline emphasis.
- **Don't** introduce bright white page backgrounds or pastel marketing themes.
- **Don't** use multiple competing CTA colors on the same surface.
- **Don't** add shadows, blur, or glass effects unless they solve a specific
  interaction problem.
- **Don't** make the UI feel playful when the product promise is evidence,
  verification, and failure avoidance.
