import type { Metadata } from "next";
import { Bebas_Neue, Source_Sans_3 } from "next/font/google";
import "./globals.css";

const displayFont = Bebas_Neue({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const bodyFont = Source_Sans_3({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Brasaland | Grilled Food Restaurant Chain",
  description:
    "Brasaland is a grilled food restaurant chain with 14 locations in Colombia and Florida. Join Brasa Points and earn rewards with every visit.",
};

const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Restaurant",
  name: "Brasaland",
  url: "https://brasaland.com",
  description:
    "Brasaland is a grilled food restaurant chain with 14 locations in Colombia and Florida.",
  servesCuisine: ["Colombian", "Latin American", "Grill"],
  areaServed: ["Colombia", "United States"],
  numberOfItems: 14,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  return (
    <html lang="en">
      <body className={`${displayFont.variable} ${bodyFont.variable} brand-body antialiased`}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
        />
        {children}
      </body>
    </html>
  );
}
