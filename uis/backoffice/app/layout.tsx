import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthProvider";
import { ThemeProvider } from "@/context/ThemeProvider";
import ProtectedShell from "@/components/auth/ProtectedShell";

const backofficeFont = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Brasaland Backoffice",
  description: "Internal dashboard for operations and business logic outputs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("brasaland_theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t;document.documentElement.style.colorScheme=t;}catch(e){document.documentElement.dataset.theme="light";}})();`,
          }}
        />
      </head>
      <body className={`${backofficeFont.className} antialiased`}>
        <ThemeProvider>
          <AuthProvider>
            <ProtectedShell>{children}</ProtectedShell>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
