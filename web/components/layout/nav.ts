import {
  ArrowLeftRight,
  Calculator,
  CircleHelp,
  Landmark,
  LayoutDashboard,
  PieChart,
  ReceiptText,
  Tags,
  Target,
  User,
  Wallet,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const menuItems: NavItem[] = [
  { href: "/", label: "Painel", icon: LayoutDashboard },
  { href: "/orcamento", label: "Orçamento", icon: Wallet },
  { href: "/metas", label: "Metas", icon: Target },
  { href: "/investimentos", label: "Investimentos", icon: PieChart },
  { href: "/simulador", label: "Simulador", icon: Calculator },
  { href: "/contas", label: "Contas", icon: Landmark },
  { href: "/faturas", label: "Faturas", icon: ReceiptText },
  { href: "/transacoes", label: "Transações", icon: ArrowLeftRight },
  { href: "/tags", label: "Tags", icon: Tags },
];

export const otherItems: NavItem[] = [
  { href: "/perfil", label: "Perfil", icon: User },
  { href: "/manutencao", label: "Manutenção", icon: Wrench },
  { href: "/faq", label: "FAQ", icon: CircleHelp },
];
