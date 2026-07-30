import type { Metadata } from "next";

import { MenuPage } from "@/components/menu/MenuPage";

export const metadata: Metadata = {
  title: "Menu | Brasaland",
  description:
    "Explore the Brasaland menu mockup: grilled meats, coastal seafood, arepas, bowls, sides, and tropical drinks for Colombia and Florida.",
};

export default function Page(): React.JSX.Element {
  return <MenuPage />;
}
