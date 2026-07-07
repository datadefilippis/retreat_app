/**
 * categoryIcons — DS2/DS5 (founder 7/7): via le emoji, icone lucide
 * PERTINENTI e COLORATE. Ogni categoria ha il suo tono, curato per
 * leggersi sia sui chip scuri degli hero sia sulle card chiare:
 * il colore dà contrasto e riconoscibilità, l'icona racconta la pratica.
 */
import React from 'react';
import {
  Flower2, Brain, Leaf, AudioLines, HandHeart, Wind, Footprints, Moon,
  Users, Dumbbell, HeartPulse, GraduationCap, Home, Package,
  CalendarDays, Sparkles,
} from 'lucide-react';

// Chiavi backend (retreat_taxonomy) + alias legacy visti nei dati.
// [icona, colore]: toni medi, saturi il giusto per vivere su scuro e chiaro.
export const CATEGORY_ICON_MAP = {
  yoga: [Flower2, '#d9a84e'],                    // loto, oro caldo
  meditazione: [Brain, '#7ec8bd'], meditation: [Brain, '#7ec8bd'],
  detox: [Leaf, '#7fbf6e'],                      // linfa
  suono: [AudioLines, '#b48fd9'], sound: [AudioLines, '#b48fd9'],
  sound_healing: [AudioLines, '#b48fd9'],
  massaggio: [HandHeart, '#e08f6a'],             // terracotta
  breathwork: [Wind, '#7fb3d9'],                 // respiro
  cammini: [Footprints, '#a3b56a'],              // sentiero
  escursioni: [Footprints, '#a3b56a'], hiking: [Footprints, '#a3b56a'],
  femminile: [Moon, '#e598b4'],                  // luna rosa
  aziendale: [Users, '#9aa7b8'],                 // team
  fitness: [Dumbbell, '#d97f7f'],
  benessere: [HeartPulse, '#e0a3a3'], wellness: [HeartPulse, '#e0a3a3'],
};

// Anime prodotto (StoreHome, blog, aggregatori).
export const TYPE_ICON_MAP = {
  eventi: [CalendarDays, '#d9a84e'], event_ticket: [CalendarDays, '#d9a84e'],
  corsi: [GraduationCap, '#7fb3d9'], course: [GraduationCap, '#7fb3d9'],
  servizi: [HandHeart, '#e08f6a'], service: [HandHeart, '#e08f6a'],
  prodotti: [Package, '#a3b56a'], physical: [Package, '#a3b56a'],
  digital: [Package, '#a3b56a'],
  affitti: [Home, '#7ec8bd'], rental: [Home, '#7ec8bd'],
};

const FALLBACK = [Sparkles, '#c9b37e'];

export function CategoryIcon({ category, className = 'h-4 w-4', colored = true }) {
  const [Icon, color] = CATEGORY_ICON_MAP[category] || FALLBACK;
  return <Icon className={className} style={colored ? { color } : undefined} aria-hidden />;
}

export function TypeIcon({ type, className = 'h-4 w-4', colored = true }) {
  const [Icon, color] = TYPE_ICON_MAP[type] || FALLBACK;
  return <Icon className={className} style={colored ? { color } : undefined} aria-hidden />;
}
