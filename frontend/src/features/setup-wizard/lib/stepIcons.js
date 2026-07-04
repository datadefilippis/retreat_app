/**
 * Icon mapping for the setup wizard (Fase 2 Track F — Step 4).
 *
 * The backend ships icon hints as kebab-case strings (`icon_key`) on each
 * SetupCTA. The frontend resolves them to actual lucide-react components
 * via this map. Decoupling icon NAMES from icon COMPONENTS lets the
 * backend evolve without ever importing UI libraries.
 *
 * Adding a new icon key:
 *   1. Pick a lucide-react icon name.
 *   2. Import it below.
 *   3. Add it to STEP_ICONS.
 *
 * Unknown keys fall back to <Circle /> so the widget never crashes on a
 * typo or a backend release that knows about an icon the frontend hasn't
 * shipped yet.
 *
 * Icon keys currently emitted by the backend (services/setup_wizard/
 * step_registry.py):
 *
 *   Global section
 *     mail-check, palette
 *
 *   Cashflow Monitor section
 *     pencil, upload, bell
 *
 *   Commerce section
 *     store, package-plus, mail, credit-card, rocket,
 *     plus-circle, zap
 *
 *   AI Assistant section
 *     sparkles
 *
 * Plus generic fallbacks used for section headers and progress.
 */

import {
  // CTA icons
  MailCheck,
  Palette,
  Pencil,
  Upload,
  Bell,
  Store,
  PackagePlus,
  Mail,
  CreditCard,
  Rocket,
  PlusCircle,
  Zap,
  Sparkles,
  // Section / generic icons
  LayoutDashboard,
  ShoppingCart,
  TrendingUp,
  Users,
  Settings,
  // Status / structural
  CheckCircle2,
  Circle,
  Lock,
} from 'lucide-react';


// CTA icons (used by SetupStepCTAs to render a leading icon on each button)
export const STEP_ICONS = Object.freeze({
  // global
  'mail-check': MailCheck,
  'palette': Palette,

  // cashflow_monitor
  'pencil': Pencil,
  'upload': Upload,
  'bell': Bell,

  // commerce
  'store': Store,
  'package-plus': PackagePlus,
  'mail': Mail,
  'credit-card': CreditCard,
  'rocket': Rocket,
  'plus-circle': PlusCircle,
  'zap': Zap,

  // ai_assistant
  'sparkles': Sparkles,
});


// Section icons (per module_key) — picked up by SetupSectionGroup
export const SECTION_ICONS = Object.freeze({
  'global': Settings,
  'cashflow_monitor': TrendingUp,
  'commerce': ShoppingCart,
  'customers_light': Users,
  'ai_assistant': Sparkles,
  'dashboard': LayoutDashboard,
});


// Status indicators
export const STATUS_ICONS = Object.freeze({
  done: CheckCircle2,
  pending: Circle,
  locked: Lock,
});


/**
 * Resolve a CTA icon component from its kebab-case key.
 * Falls back to <Circle /> when the key is unknown.
 */
export function getCtaIcon(iconKey) {
  if (!iconKey) return null;
  return STEP_ICONS[iconKey] || Circle;
}

/**
 * Resolve a section icon component from its module_key.
 * Falls back to <LayoutDashboard /> for unknown modules.
 */
export function getSectionIcon(moduleKey) {
  return SECTION_ICONS[moduleKey] || LayoutDashboard;
}
