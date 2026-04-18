import "./globals.css";

export const metadata = {
  title: "SafeHarbor — AI Gambling Addiction Support",
  description:
    "Confidential counseling, country-specific legal guidance, and crisis-aware support.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased text-gray-900 bg-gray-50 min-h-screen">
        {children}
      </body>
    </html>
  );
}
