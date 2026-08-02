import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Fikak App",
  description: "Next.js app connected to MongoDB Atlas",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
