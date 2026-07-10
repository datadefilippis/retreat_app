/**
 * i18n-admin — traduzioni del BACK-OFFICE, fuori dal bundle pubblico (PL17).
 *
 * Perché: i 18 namespace admin ×4 lingue pesavano ~307KB gzip DENTRO il
 * main.js — il 42% del bundle che un visitatore delle landing scarica
 * senza mai usarlo. Questo modulo li registra su i18next e viene
 * importato (side-effect) da components/Layout, il guscio che OGNI
 * pagina admin usa: vive quindi nei chunk lazy dell'admin e viene
 * valutato PRIMA del render delle pagine — nessun flash di fallback.
 *
 * Il pubblico (common, auth, landings, storefront, catalog, legal,
 * customer_*, prelaunch) resta sincrono in i18n.js — così come
 * settings e modules_page, usati dai banner billing/paywall EAGER.
 *
 * Chi AGGIUNGE un namespace admin lo aggiunge QUI, non in i18n.js.
 */
import i18n from './i18n';

import dashboardIt from './locales/it/dashboard.json';
import customersLightIt from './locales/it/customers_light.json';
import customerInsightsIt from './locales/it/customerInsights.json';
import teamIt from './locales/it/team.json';
import productCatalogIt from './locales/it/product_catalog.json';
import productCostIt from './locales/it/product_cost.json';
import productsIt from './locales/it/products.json';
import entitiesIt from './locales/it/entities.json';
import ordersIt from './locales/it/orders.json';
import calendarIt from './locales/it/calendar.json';
import dataIntegrityIt from './locales/it/data_integrity.json';
import storeSettingsIt from './locales/it/store_settings.json';
import setupWizardIt from './locales/it/setup_wizard.json';
import storesIt from './locales/it/stores.json';
import posIt from './locales/it/pos.json';
import reservationsIt from './locales/it/reservations.json';
import newsletterIt from './locales/it/newsletter.json';
import cashflowMonitorIt from './locales/it/cashflow_monitor.json';

import dashboardEn from './locales/en/dashboard.json';
import customersLightEn from './locales/en/customers_light.json';
import customerInsightsEn from './locales/en/customerInsights.json';
import teamEn from './locales/en/team.json';
import productCatalogEn from './locales/en/product_catalog.json';
import productCostEn from './locales/en/product_cost.json';
import productsEn from './locales/en/products.json';
import entitiesEn from './locales/en/entities.json';
import ordersEn from './locales/en/orders.json';
import calendarEn from './locales/en/calendar.json';
import dataIntegrityEn from './locales/en/data_integrity.json';
import storeSettingsEn from './locales/en/store_settings.json';
import setupWizardEn from './locales/en/setup_wizard.json';
import storesEn from './locales/en/stores.json';
import posEn from './locales/en/pos.json';
import reservationsEn from './locales/en/reservations.json';
import newsletterEn from './locales/en/newsletter.json';
import cashflowMonitorEn from './locales/en/cashflow_monitor.json';

import dashboardDe from './locales/de/dashboard.json';
import customersLightDe from './locales/de/customers_light.json';
import customerInsightsDe from './locales/de/customerInsights.json';
import teamDe from './locales/de/team.json';
import productCatalogDe from './locales/de/product_catalog.json';
import productCostDe from './locales/de/product_cost.json';
import productsDe from './locales/de/products.json';
import entitiesDe from './locales/de/entities.json';
import ordersDe from './locales/de/orders.json';
import calendarDe from './locales/de/calendar.json';
import dataIntegrityDe from './locales/de/data_integrity.json';
import storeSettingsDe from './locales/de/store_settings.json';
import setupWizardDe from './locales/de/setup_wizard.json';
import storesDe from './locales/de/stores.json';
import posDe from './locales/de/pos.json';
import reservationsDe from './locales/de/reservations.json';
import newsletterDe from './locales/de/newsletter.json';
import cashflowMonitorDe from './locales/de/cashflow_monitor.json';

import dashboardFr from './locales/fr/dashboard.json';
import customersLightFr from './locales/fr/customers_light.json';
import customerInsightsFr from './locales/fr/customerInsights.json';
import teamFr from './locales/fr/team.json';
import productCatalogFr from './locales/fr/product_catalog.json';
import productCostFr from './locales/fr/product_cost.json';
import productsFr from './locales/fr/products.json';
import entitiesFr from './locales/fr/entities.json';
import ordersFr from './locales/fr/orders.json';
import calendarFr from './locales/fr/calendar.json';
import dataIntegrityFr from './locales/fr/data_integrity.json';
import storeSettingsFr from './locales/fr/store_settings.json';
import setupWizardFr from './locales/fr/setup_wizard.json';
import storesFr from './locales/fr/stores.json';
import posFr from './locales/fr/pos.json';
import reservationsFr from './locales/fr/reservations.json';
import newsletterFr from './locales/fr/newsletter.json';
import cashflowMonitorFr from './locales/fr/cashflow_monitor.json';

const ADMIN_BUNDLES = {
  it: { dashboard: dashboardIt, customers_light: customersLightIt, customerInsights: customerInsightsIt, team: teamIt, product_catalog: productCatalogIt, product_cost: productCostIt, products: productsIt, entities: entitiesIt, orders: ordersIt, calendar: calendarIt, data_integrity: dataIntegrityIt, store_settings: storeSettingsIt, setup_wizard: setupWizardIt, stores: storesIt, pos: posIt, reservations: reservationsIt, newsletter: newsletterIt, cashflow_monitor: cashflowMonitorIt },
  en: { dashboard: dashboardEn, customers_light: customersLightEn, customerInsights: customerInsightsEn, team: teamEn, product_catalog: productCatalogEn, product_cost: productCostEn, products: productsEn, entities: entitiesEn, orders: ordersEn, calendar: calendarEn, data_integrity: dataIntegrityEn, store_settings: storeSettingsEn, setup_wizard: setupWizardEn, stores: storesEn, pos: posEn, reservations: reservationsEn, newsletter: newsletterEn, cashflow_monitor: cashflowMonitorEn },
  de: { dashboard: dashboardDe, customers_light: customersLightDe, customerInsights: customerInsightsDe, team: teamDe, product_catalog: productCatalogDe, product_cost: productCostDe, products: productsDe, entities: entitiesDe, orders: ordersDe, calendar: calendarDe, data_integrity: dataIntegrityDe, store_settings: storeSettingsDe, setup_wizard: setupWizardDe, stores: storesDe, pos: posDe, reservations: reservationsDe, newsletter: newsletterDe, cashflow_monitor: cashflowMonitorDe },
  fr: { dashboard: dashboardFr, customers_light: customersLightFr, customerInsights: customerInsightsFr, team: teamFr, product_catalog: productCatalogFr, product_cost: productCostFr, products: productsFr, entities: entitiesFr, orders: ordersFr, calendar: calendarFr, data_integrity: dataIntegrityFr, store_settings: storeSettingsFr, setup_wizard: setupWizardFr, stores: storesFr, pos: posFr, reservations: reservationsFr, newsletter: newsletterFr, cashflow_monitor: cashflowMonitorFr },
};

// Idempotente: addResourceBundle con deep+overwrite non duplica nulla se
// il modulo venisse valutato due volte (HMR, chunk condivisi).
for (const [lng, bundles] of Object.entries(ADMIN_BUNDLES)) {
  for (const [ns, data] of Object.entries(bundles)) {
    i18n.addResourceBundle(lng, ns, data, true, true);
  }
}

export default null;
