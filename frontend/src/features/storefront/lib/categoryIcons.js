/**
 * categoryIcons — DS2 (feedback founder 7/7): via le emoji dal
 * marketplace, icone lucide coerenti col brand. UNICA mappa
 * categoria→icona per directory, aggregatori, card e placeholder.
 */
import React from 'react';
import {
  Flower2, Sparkles, Leaf, Waves, Hand, Wind, Mountain, Moon,
  Building2, Dumbbell, HeartHandshake, GraduationCap, Home, Package,
  Wrench, CalendarDays,
} from 'lucide-react';

// Chiavi backend (retreat_taxonomy) + alias legacy visti nei dati.
export const CATEGORY_ICON_MAP = {
  yoga: Flower2,
  meditazione: Sparkles, meditation: Sparkles,
  detox: Leaf,
  suono: Waves, sound: Waves, sound_healing: Waves,
  massaggio: Hand,
  breathwork: Wind,
  cammini: Mountain, escursioni: Mountain, hiking: Mountain,
  femminile: Moon,
  aziendale: Building2,
  fitness: Dumbbell,
  benessere: HeartHandshake, wellness: HeartHandshake,
};

// Anime prodotto (StoreHome, Esperienze).
export const TYPE_ICON_MAP = {
  eventi: CalendarDays, event_ticket: CalendarDays,
  corsi: GraduationCap, course: GraduationCap,
  servizi: Wrench, service: HeartHandshake,
  prodotti: Package, physical: Package, digital: Package,
  affitti: Home, rental: Home,
};

export function CategoryIcon({ category, className = 'h-4 w-4' }) {
  const Icon = CATEGORY_ICON_MAP[category] || Sparkles;
  return <Icon className={className} aria-hidden />;
}

export function TypeIcon({ type, className = 'h-4 w-4' }) {
  const Icon = TYPE_ICON_MAP[type] || Sparkles;
  return <Icon className={className} aria-hidden />;
}
