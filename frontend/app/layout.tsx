import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const notoSansKr = localFont({
  variable: "--font-noto-sans-kr",
  display: "swap",
  src: [
    { path: "../public/font/NotoSansKR-Thin.ttf", weight: "100", style: "normal" },
    { path: "../public/font/NotoSansKR-ExtraLight.ttf", weight: "200", style: "normal" },
    { path: "../public/font/NotoSansKR-Light.ttf", weight: "300", style: "normal" },
    { path: "../public/font/NotoSansKR-Regular.ttf", weight: "400", style: "normal" },
    { path: "../public/font/NotoSansKR-Medium.ttf", weight: "500", style: "normal" },
    { path: "../public/font/NotoSansKR-SemiBold.ttf", weight: "600", style: "normal" },
    { path: "../public/font/NotoSansKR-Bold.ttf", weight: "700", style: "normal" },
    { path: "../public/font/NotoSansKR-ExtraBold.ttf", weight: "800", style: "normal" },
    { path: "../public/font/NotoSansKR-Black.ttf", weight: "900", style: "normal" },
  ],
});

const gmarketSans = localFont({
  variable: "--font-gmarket-sans",
  display: "swap",
  src: [
    { path: "../public/font/GmarketSansTTFLight.ttf", weight: "300", style: "normal" },
    { path: "../public/font/GmarketSansTTFMedium.ttf", weight: "500", style: "normal" },
    { path: "../public/font/GmarketSansTTFBold.ttf", weight: "700", style: "normal" },
  ],
});

export const metadata: Metadata = {
  title: "TechTree",
  description: "AI 가상 면접 서비스, TechTree",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body
        className={`${notoSansKr.variable} ${gmarketSans.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
