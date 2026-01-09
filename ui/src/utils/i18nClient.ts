// Global client-side translation loader
import en from '../i18n/en.json';
import es from '../i18n/es.json';

const translations = { en, es };

const getNestedValue = (obj: any, path: string): string => {
  return path.split('.').reduce((current, key) => current?.[key], obj) ?? path;
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
