/**
 * Lo stato dei Prodotti per gli operatori (founder, 6/10/2026 sera):
 * il modulo e' pronto (P0+P1+P2+consolidamento) ma esce in ANTEPRIMA:
 * la scheda in Strumenti si vede, leggermente oscurata, e dice che sta
 * arrivando; le pagine /prodotti/* restano chiuse (rimandano a
 * Strumenti). Quando il founder da' il via, questo diventa `true`: un
 * solo cambio, un giro frontend.
 *
 * Il backend NON cambia: le API /prodotti stanno dietro require_module e
 * il profilo pubblico mostra solo prodotti pubblicati (oggi nessuno).
 */
export const PRODOTTI_UI_PRONTA = false;
