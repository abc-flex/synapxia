// Internationalization (i18n) support
const translations = {
  en: {
    header: {
      subtitle: "System for Insight, Adoption, Practice & eXpansion through Intelligent Agents"
    },
    sidebar: {
      dashboard: "Dashboard",
      assignments: "Assignments",
      reports: "Reports",
      settings: "Settings"
    },
    dashboard: {
      title: "Assignments Dashboard",
      selectDimension: "Select Dimension:"
    },
    dimensions: {
      aiAdoption: "AI Adoption",
      vacation: "Vacation",
      englishLevel: "English Level"
    },
    modal: {
      email: "Email:",
      role: "Role:",
      team: "Team:",
      date: "Date:",
      observation: "Observation:",
      currentMetric: "Current Metric:",
      saveMetric: "Save Metric",
      addEntry: "Add New Entry"
    },
    metrics: {
      high: "High",
      medium: "Medium",
      low: "Low"
    },
    footer: {
      copyright: "© 2025 SinapxIA. All rights reserved."
    },
    notifications: {
      metricSaved: "Metric updated successfully",
      featureComingSoon: "Feature coming soon: Add new entry"
    }
  },
  es: {
    header: {
      subtitle: "Sistema para Insight, Adopción, Práctica y eXpansión a través de Agentes Inteligentes"
    },
    sidebar: {
      dashboard: "Tablero",
      assignments: "Asignaciones",
      reports: "Reportes",
      settings: "Configuración"
    },
    dashboard: {
      title: "Tablero de Asignaciones",
      selectDimension: "Seleccionar Dimensión:"
    },
    dimensions: {
      aiAdoption: "Adopción de IA",
      vacation: "Vacaciones",
      englishLevel: "Nivel de Inglés"
    },
    modal: {
      email: "Correo:",
      role: "Rol:",
      team: "Equipo:",
      date: "Fecha:",
      observation: "Observación:",
      currentMetric: "Métrica Actual:",
      saveMetric: "Guardar Métrica",
      addEntry: "Agregar Nueva Entrada"
    },
    metrics: {
      high: "Alto",
      medium: "Medio",
      low: "Bajo"
    },
    footer: {
      copyright: "© 2025 SinapxIA. Todos los derechos reservados."
    },
    notifications: {
      metricSaved: "Métrica actualizada exitosamente",
      featureComingSoon: "Funcionalidad próximamente: Agregar nueva entrada"
    }
  }
};

let currentLanguage = 'es';

// Initialize i18n
function initializeI18n() {
  // Try to get language from localStorage or browser
  const savedLanguage = localStorage.getItem('language');
  const browserLanguage = navigator.language.split('-')[0];

  currentLanguage = savedLanguage || (browserLanguage === 'es' ? 'es' : 'en');

  // Set the language selector
  const languageSelector = document.getElementById('languageSelector');
  if (languageSelector) {
    languageSelector.value = currentLanguage;
  }

  // Apply translations
  applyTranslations();
}

// Change language
function changeLanguage(lang) {
  currentLanguage = lang;
  localStorage.setItem('language', lang);
  applyTranslations();
}

// Apply translations to the page
function applyTranslations() {
  const elements = document.querySelectorAll('[data-i18n]');

  elements.forEach(element => {
    const key = element.getAttribute('data-i18n');
    const translation = getNestedTranslation(key);

    if (translation) {
      // Handle different element types
      if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        element.placeholder = translation;
      } else if (element.tagName === 'OPTION') {
        element.textContent = translation;
      } else {
        element.textContent = translation;
      }
    }
  });
}

// Get nested translation
function getNestedTranslation(key) {
  const keys = key.split('.');
  let value = translations[currentLanguage];

  for (const k of keys) {
    if (value && value[k]) {
      value = value[k];
    } else {
      return null;
    }
  }

  return value;
}

// Translate function for use in JavaScript
function translate(key) {
  return getNestedTranslation(key);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    translate,
    changeLanguage,
    initializeI18n
  };
}
