import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Sans_Condensed } from "next/font/google";

// RU: Шрифты централизованы здесь, чтобы маркетинговый и операторский слой не расходились по font imports.
export const fontBody = IBM_Plex_Sans({
  subsets: ["latin", "cyrillic-ext"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
  display: "swap"
});

export const fontHeading = IBM_Plex_Sans_Condensed({
  subsets: ["latin", "cyrillic-ext"],
  variable: "--font-heading",
  weight: ["500", "600", "700"],
  display: "swap"
});

export const fontMono = IBM_Plex_Mono({
  subsets: ["latin", "cyrillic-ext"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap"
});
