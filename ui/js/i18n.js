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
      genAIDevs: "GenAI Adoption for Devs",
      genAIQA: "GenAI Adoption for QA"
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
      noUsage: "No Usage",
      low: "Low",
      moderate: "Moderate",
      high: "High",
      veryHigh: "Very High"
    },
    metricsDescriptions: {
      genAIDevs: {
        NO_USAGE: "No GitHub Copilot, Cursor, Windsurf or Antigravity configured",
        LOW: "Chat-only for small scripts and code suggestions",
        MODERATE: "Agent mode for basic generation, refactors, and fixes",
        HIGH: "Custom agents and MCP for advanced generation and Azure DevOps integration",
        VERY_HIGH: "Agents, multi-agents, and advanced MCP for autonomous development"
      },
      genAIQA: {
        NO_USAGE: "No AI testing tools configured",
        LOW: "Chat-only for small scripts and test suggestions",
        MODERATE: "Agent mode for basic test generation and issue review",
        HIGH: "Custom agents and MCP to run tests and integrate with Azure DevOps",
        VERY_HIGH: "Agents, multi-agents, and advanced MCP for autonomous testing"
      }
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
      genAIDevs: "Adopción GenAI para Devs",
      genAIQA: "Adopción GenAI para QA"
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
      noUsage: "Sin Uso",
      low: "Bajo",
      moderate: "Moderado",
      high: "Alto",
      veryHigh: "Muy Alto"
    },
    metricsDescriptions: {
      genAIDevs: {
        NO_USAGE: "No configurado Github Copilot, Cursor, Windsurf o Antigravity",
        LOW: "Chat en modo consulta para pequenos scripts y sugerencias de codigo",
        MODERATE: "Modo agente para generacion basica, refactorizacion y correccion de problemas",
        HIGH: "Agentes customizados y MCP para generacion avanzada e interaccion con Azure DevOps",
        VERY_HIGH: "Agentes, multi-agentes y MCP avanzado para desarrollo con autonomia"
      },
      genAIQA: {
        NO_USAGE: "No hay herramientas con IA configuradas para la realizacion de pruebas",
        LOW: "Chat en modo consulta para pequenos scripts y sugerencias de pruebas",
        MODERATE: "Modo agente para generacion basica de pruebas y revision de problemas",
        HIGH: "Agentes customizados y MCP para realizar pruebas e interactuar con Azure DevOps",
        VERY_HIGH: "Agentes, multi-agentes y MCP avanzado para pruebas autonomas"
      }
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
