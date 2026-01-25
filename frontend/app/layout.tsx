// Root layout - minimal, just passes through to locale-specific layouts
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
