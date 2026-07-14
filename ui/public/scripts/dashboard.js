import { employeesData } from "../data/data.js";
import { translations } from "../../src/data/translations.js";

const rolesOrder = ["BACK", "FRONT", "QA"];
const teamsOrder = ["HADES", "SKYNET", "KEPLER", "PIXEL", "ROCKET"];
const dimensions = ["aiAdoption", "vacation", "englishLevel"];
const metricStyles = {
  Alto: "bg-emerald-500 hover:bg-emerald-600",
  Medio: "bg-amber-400 hover:bg-amber-500",
  Bajo: "bg-red-500 hover:bg-red-600"
};

let currentLanguage = "es";
let currentDimension = "aiAdoption";
let employees = employeesData.map((employee) => ({ ...employee }));
let currentEmployeeEmail = null;
let notificationTimer = null;

const modal = document.getElementById("employeeModal");
const dashboardContainer = document.getElementById("dashboardGrid");
const dimensionSelect = document.getElementById("dimensionSelect");
const languageSelector = document.getElementById("languageSelector");
const modalMetricSelect = document.getElementById("modalMetricSelect");
const modalName = document.getElementById("modalEmployeeName");
const modalEmail = document.getElementById("modalEmployeeEmail");
const modalRole = document.getElementById("modalEmployeeRole");
const modalTeam = document.getElementById("modalEmployeeTeam");
const modalDate = document.getElementById("modalEmployeeDate");
const modalObservation = document.getElementById("modalEmployeeObservation");
const saveMetricBtn = document.getElementById("saveMetricBtn");
const addEntryBtn = document.getElementById("addEntryBtn");
const closeModalBtn = document.getElementById("closeModalBtn");

const getTranslationValue = (key) => {
  const parts = key.split(".");
  let node = translations[currentLanguage];
  for (const part of parts) {
    if (node && part in node) {
      node = node[part];
    } else {
      return null;
    }
  }
  return typeof node === "string" ? node : null;
};

const applyTranslations = () => {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const translation = getTranslationValue(key);
    if (translation) {
      if (element.tagName === "INPUT" || element.tagName === "TEXTAREA") {
        element.placeholder = translation;
      } else if (element.tagName === "OPTION") {
        element.textContent = translation;
      } else {
        element.textContent = translation;
      }
    }
  });
};

const renderLanguageOptions = () => {
  if (!languageSelector) return;
  languageSelector.innerHTML = "";
  const options = translations[currentLanguage].labels.languageOptions;
  Object.entries(options).forEach(([code, label]) => {
    const option = document.createElement("option");
    option.value = code;
    option.textContent = label;
    languageSelector.appendChild(option);
  });
  languageSelector.value = currentLanguage;
};

const renderDimensionOptions = () => {
  if (!dimensionSelect) return;
  dimensionSelect.innerHTML = "";
  dimensions.forEach((key) => {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = translations[currentLanguage].dimensions[key];
    if (key === currentDimension) {
      option.selected = true;
    }
    dimensionSelect.appendChild(option);
  });
};

const renderModalMetricOptions = () => {
  if (!modalMetricSelect) return;
  modalMetricSelect.innerHTML = "";
  metricOptions.forEach((entry) => {
    const option = document.createElement("option");
    option.value = entry.value;
    option.textContent = getTranslationValue(entry.key) || entry.value;
    modalMetricSelect.appendChild(option);
  });
};

const metricOptions = [
  { value: "Alto", key: "metrics.high" },
  { value: "Medio", key: "metrics.medium" },
  { value: "Bajo", key: "metrics.low" }
];

const groupedEmployees = () => {
  const map = {};
  employees.forEach((employee) => {
    const key = `${employee.role}-${employee.team}`;
    if (!map[key]) {
      map[key] = [];
    }
    map[key].push(employee);
  });
  return map;
};

const showNotification = (message) => {
  if (!message) return;
  if (notificationTimer) {
    clearTimeout(notificationTimer);
  }
  const notification = document.createElement("div");
  notification.className =
    "fixed top-6 right-6 bg-indigo-600 text-white px-8 py-4 rounded-lg shadow-lg z-50 animate-slideIn";
  notification.textContent = message;
  document.body.appendChild(notification);
  notificationTimer = setTimeout(() => {
    notification.classList.add("animate-fadeOut");
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
};

const openModal = (email) => {
  currentEmployeeEmail = email;
  const employee = employees.find((entry) => entry.email === email);
  if (!employee) return;
  modalName.textContent = employee.name;
  modalEmail.textContent = employee.email;
  modalRole.textContent = employee.role;
  modalTeam.textContent = employee.team;
  modalDate.textContent = employee.date;
  modalObservation.textContent = employee.observation;
  modalMetricSelect.value = employee.metric;
  modal.classList.remove("hidden");
};

const closeModal = () => {
  currentEmployeeEmail = null;
  modal.classList.add("hidden");
};

const saveMetric = () => {
  if (!currentEmployeeEmail) return;
  const newMetric = modalMetricSelect.value;
  employees = employees.map((entry) =>
    entry.email === currentEmployeeEmail ? { ...entry, metric: newMetric } : entry
  );
  showNotification(translations[currentLanguage].notifications.metricSaved);
  renderDashboard();
  closeModal();
};

const addEntry = () => {
  showNotification(translations[currentLanguage].notifications.featureComingSoon);
  closeModal();
};

const renderDashboard = () => {
  if (!dashboardContainer) return;
  const teams = teamsOrder.filter((team) =>
    employees.some((employee) => employee.team === team)
  );
  const roles = rolesOrder.filter((role) =>
    employees.some((employee) => employee.role === role)
  );
  const map = groupedEmployees();
  const metricLabelMap = {
    Alto: translations[currentLanguage].metrics.high,
    Medio: translations[currentLanguage].metrics.medium,
    Bajo: translations[currentLanguage].metrics.low
  };

  let table = "<div class='min-w-[800px]'><table class='w-full border-collapse'><thead><tr>";
  table +=
    "<th class='bg-indigo-600 text-white text-left px-4 py-3 font-semibold sticky top-0 z-10 border border-gray-200'>Role / Team</th>";
  teams.forEach((team) => {
    table += `<th class='bg-gray-100 text-gray-900 px-4 py-3 font-semibold text-center border border-gray-200 sticky top-0 z-10'>${team}</th>`;
  });
  table += "</tr></thead><tbody>";

  roles.forEach((role) => {
    table += `<tr><td class='bg-gray-50 text-gray-900 px-4 py-3 font-semibold border border-gray-200'>${role}</td>`;
    teams.forEach((team) => {
      const key = `${role}-${team}`;
      const entries = map[key] || [];
      table += "<td class='px-4 py-3 border border-gray-200 text-center'>";
      if (entries.length > 0) {
        table += "<div class='flex flex-wrap gap-2 justify-center items-center min-h-[60px]'>";
        entries.forEach((entry) => {
          const initials = entry.name
            .split(" ")
            .filter(Boolean)
            .map((chunk) => chunk[0])
            .slice(0, 2)
            .join("");
          table += `
            <button
              type='button'
              class='avatar relative z-20 w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm text-white shadow-md transition-transform focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 ${metricStyles[entry.metric]}'
              aria-label='${entry.name} - ${metricLabelMap[entry.metric]}'
              data-email='${entry.email}'
            >
              ${initials}
              <span class='avatar-tooltip absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap'>${entry.name}</span>
            </button>
          `;
        });
        table += "</div>";
      } else {
        table += "<p class='text-xs text-gray-400'>—</p>";
      }
      table += "</td>";
    });
    table += "</tr>";
  });

  table += "</tbody></table></div>";
  dashboardContainer.innerHTML = table;
  dashboardContainer.querySelectorAll("button[data-email]").forEach((button) => {
    button.addEventListener("click", () => openModal(button.dataset.email));
  });
};

const init = () => {
  if (typeof window === "undefined") {
    return;
  }

  const storedLanguage = localStorage.getItem("sinapxia-language");
  if (storedLanguage && translations[storedLanguage]) {
    currentLanguage = storedLanguage;
  } else {
    const browserLang = navigator.language?.startsWith("es") ? "es" : "en";
    currentLanguage = browserLang;
  }

  renderLanguageOptions();
  renderDimensionOptions();
  renderModalMetricOptions();
  applyTranslations();
  renderDashboard();

  dimensionSelect.addEventListener("change", (event) => {
    currentDimension = event.target.value;
    renderDimensionOptions();
    renderDashboard();
  });

  languageSelector.addEventListener("change", (event) => {
    currentLanguage = event.target.value;
    localStorage.setItem("sinapxia-language", currentLanguage);
    renderLanguageOptions();
    renderDimensionOptions();
    renderModalMetricOptions();
    applyTranslations();
    renderDashboard();
  });

  saveMetricBtn.addEventListener("click", saveMetric);
  addEntryBtn.addEventListener("click", addEntry);
  closeModalBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModal();
    }
  });
};

init();
