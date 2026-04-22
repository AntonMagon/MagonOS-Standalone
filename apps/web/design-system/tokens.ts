// RU: Набор токенов маленький намеренно, чтобы shell оставался визуально цельным и управляемым.
export const designTokens = {
  colors: {
    paper: "#F3EBDD",
    milk: "#F7F4EC",
    ink: "#2B2E34",
    cobalt: "#225BFF",
    signal: "#63E3FF",
    danger: "#D94B3D",
    lime: "#C9FF4D"
  },
  radii: {
    xl: "1.75rem",
    lg: "1.25rem",
    md: "0.9rem",
    sm: "0.65rem"
  },
  spacing: {
    section: "clamp(4rem, 8vw, 7rem)",
    gutter: "clamp(1.25rem, 3vw, 2rem)",
    grid: "clamp(1rem, 2vw, 1.5rem)"
  },
  animation: {
    durationFast: "150ms",
    durationBase: "240ms",
    durationSlow: "420ms"
  }
} as const;
