// Global client-side translation loader
import en from '../i18n/en.json';
import es from '../i18n/es.json';

const translations = { en, es };

const getNestedValue = (obj: any, path: string): string => {
  return path.split('.').reduce((current, key) => current?.[key], obj) ?? path;
};

/**
 * Look up a single translation for the current locale (read from
 * localStorage['lang']). Falls back to the key itself when missing. Use this
 * from client islands that need to set a label imperatively (e.g. the vote
 * buttons swapping between "Helpful" and "Remove vote" when toggled).
 */
export const translate = (key: string): string => {
  const lang =
    (typeof localStorage !== 'undefined' && localStorage.getItem('lang')) || 'en';
  const locale = (lang === 'es' ? 'es' : 'en') as keyof typeof translations;
  return getNestedValue(translations[locale], key);
};

export const loadClientTranslations = () => {
  const lang = localStorage.getItem('lang') || 'en';
  const locale = (lang === 'es' ? 'es' : 'en') as keyof typeof translations;

  // Update all elements with data-i18n attribute
  const elements = document.querySelectorAll('[data-i18n]');
  elements.forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (key) {
      const translation = getNestedValue(translations[locale], key);
      if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        (element as HTMLInputElement).placeholder = translation;
      } else {
        element.textContent = translation;
      }
    }
  });

  // Update elements with data-i18n-title attribute
  const titleElements = document.querySelectorAll('[data-i18n-title]');
  titleElements.forEach((element) => {
    const key = element.getAttribute('data-i18n-title');
    if (key) {
      const translation = getNestedValue(translations[locale], key);
      element.setAttribute('title', translation);
    }
  });

  // Update elements with data-i18n-placeholder attribute
  const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
  placeholderElements.forEach((element) => {
    const key = element.getAttribute('data-i18n-placeholder');
    if (key) {
      const translation = getNestedValue(translations[locale], key);
      (element as HTMLInputElement).placeholder = translation;
    }
  });

  // Update elements with data-i18n-aria-label attribute
  // (Matches ClientTranslations.astro's behavior so both runtimes are equivalent.)
  const ariaElements = document.querySelectorAll('[data-i18n-aria-label]');
  ariaElements.forEach((element) => {
    const key = element.getAttribute('data-i18n-aria-label');
    if (key) {
      const translation = getNestedValue(translations[locale], key);
      element.setAttribute('aria-label', translation);
    }
  });

  // Dispatch custom event for other components to react
  window.dispatchEvent(new CustomEvent('languageChanged', { detail: { locale } }));
};

// Auto-load on DOMContentLoaded
if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadClientTranslations);
  } else {
    loadClientTranslations();
  }
}
