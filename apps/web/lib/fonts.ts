import { IBM_Plex_Mono, Manrope, Space_Grotesk } from "next/font/google";

export const fontBody = Manrope({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap"
});

export const fontHeading = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap"
});

export const fontMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap"
});
