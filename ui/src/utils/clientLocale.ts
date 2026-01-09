// Client-side locale management
export const getClientLocale = (): string => {
  if (typeof window === 'undefined') return 'en';

  const stored = localStorage.getItem('lang');
  if (stored === 'en' || stored === 'es') {
    return stored;
  }

  const browserLang = navigator.language.split('-')[0];
  const defaultLang = browserLang === 'es' ? 'es' : 'en';
  localStorage.setItem('lang', defaultLang);
  return defaultLang;
};

export const setClientLocale = (lang: string) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem('lang', lang);
};
