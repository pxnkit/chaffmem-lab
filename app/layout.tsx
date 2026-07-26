import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

const title = "ChaffMem Lab | Memory Availability Research";
const description =
  "A deterministic research instrument for measuring storage, retrieval, behavioral, and temporal availability in bounded agent memory.";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const image = `${origin}/og.png`;

  return {
    title,
    description,
    applicationName: "ChaffMem Lab",
    authors: [{ name: "pxnkit" }],
    creator: "pxnkit",
    category: "research",
    icons: {
      icon: "/icon.png",
      shortcut: "/icon.png",
    },
    openGraph: {
      title,
      description,
      type: "website",
      images: [{ url: image, width: 1200, height: 630, alt: "ChaffMem Lab research interface" }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [image],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
