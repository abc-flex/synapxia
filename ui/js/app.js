// Application state
const STORAGE_KEY = 'employeesData';
const METRIC_LEVELS = ['UNDEFINED', 'NO_USAGE', 'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH'];
const LEGACY_METRIC_MAP = {
    'ALTO': 'HIGH',
    'ALTA': 'HIGH',
    'MEDIO': 'MODERATE',
    'MEDIA': 'MODERATE',
    'BAJO': 'LOW',
    'BAJA': 'LOW'
};
let employeesData = [];
let currentDimension = 'genAIDevs';
let currentEmployee = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    initializeI18n();
    await loadEmployeesData();
    renderDashboard();
    setupEventListeners();
});

// Load data from localStorage first, then fallback to bundled JSON, then seed file
async function loadEmployeesData() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
        employeesData = normalizeEmployeesData(JSON.parse(stored));
        persistEmployeesData();
        return;
    }

    try {
        const response = await fetch('data/data.json');
        if (!response.ok) throw new Error('Failed to load data.json');
        employeesData = normalizeEmployeesData(await response.json());
        persistEmployeesData();
    } catch (err) {
        console.error('Error loading employees data:', err);
        if (Array.isArray(window.employeesSeedData)) {
            employeesData = normalizeEmployeesData(window.employeesSeedData);
            persistEmployeesData();
        } else {
            employeesData = [];
        }
    }
}

// Convert legacy metric labels to the new GenAI levels
function normalizeEmployeesData(data) {
    return data.map(emp => ({
        ...emp,
        metric: normalizeMetricValue(emp.metric)
    }));
}

function normalizeMetricValue(metric) {
    if (!metric) return 'NO_USAGE';
    const candidate = metric.toString().trim().toUpperCase().replace(/\s+/g, '_');
    if (METRIC_LEVELS.includes(candidate)) return candidate;
    if (LEGACY_METRIC_MAP[candidate]) return LEGACY_METRIC_MAP[candidate];
    return 'NO_USAGE';
}

function setAllMetricsToNoUsage(list) {
    return list.map(emp => ({ ...emp, metric: 'NO_USAGE' }));
}

function persistEmployeesData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(employeesData));
}

// Setup event listeners
function setupEventListeners() {
    // Dimension selector
    const dimensionSelect = document.getElementById('dimensionSelect');
    dimensionSelect.addEventListener('change', (e) => {
        currentDimension = e.target.value;
        renderDashboard();
        refreshMetricSelectOptions();
    });

    // Modal close button
    const modal = document.getElementById('employeeModal');
    const closeBtn = modal.querySelector('.close');
    closeBtn.addEventListener('click', closeModal);

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Save metric button
    const saveMetricBtn = document.getElementById('saveMetricBtn');
    saveMetricBtn.addEventListener('click', saveMetric);

    // Add entry button
    const addEntryBtn = document.getElementById('addEntryBtn');
    addEntryBtn.addEventListener('click', addNewEntry);

    // Language selector
    const languageSelector = document.getElementById('languageSelector');
    languageSelector.addEventListener('change', (e) => {
        changeLanguage(e.target.value);
        refreshMetricSelectOptions();
    });

    // Hidden export button (aria-hidden true) still wired for manual trigger
    const exportBtn = document.getElementById('exportDataBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportCurrentData);
    }
}

// Render the dashboard grid
function renderDashboard() {
    const container = document.getElementById('dashboardGrid');
    const filteredEmployees = getEmployeesByDimension();
    const roles = getUniqueRoles(filteredEmployees);
    const teams = getUniqueTeams(filteredEmployees);

    let html = '<table class="w-full border-collapse min-w-[800px]"><thead><tr>';
    html += '<th class="bg-indigo-600 text-white text-left px-4 py-3 font-semibold sticky top-0 z-5 border border-gray-200">Role / Team</th>';

    // Create team headers
    teams.forEach(team => {
        html += `<th class="bg-gray-100 text-gray-900 px-4 py-3 font-semibold text-center border border-gray-200 sticky top-0 z-5">${team}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Create rows for each role
    roles.forEach(role => {
        html += '<tr>';
        html += `<td class="bg-gray-50 text-gray-900 px-4 py-3 font-semibold border border-gray-200">${role}</td>`;

        // Create cells for each team
        teams.forEach(team => {
            const employees = getEmployeesByRoleAndTeam(role, team, filteredEmployees);
            html += '<td class="px-4 py-3 border border-gray-200 text-center">';

            if (employees.length > 0) {
                html += '<div class="flex flex-wrap gap-2 justify-center items-center min-h-[60px]">';
                employees.forEach(emp => {
                    const initials = getInitials(emp.name);
                    const metricClass = getMetricColorClass(emp.metric);
                    html += `
                        <div class="avatar w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm cursor-pointer transition-transform hover:scale-110 relative z-20 ${metricClass}" 
                             onclick="openEmployeeModal('${emp.email}')"
                             title="${emp.name}">
                            ${initials}
                            <div class="avatar-tooltip absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">${emp.name}</div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            html += '</td>';
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Get metric color class
function getMetricColorClass(metric) {
    const colorMap = {
        // gray: undefined or no data
        UNDEFINED: "bg-slate-100 text-slate-700 ring-1 ring-slate-200 shadow-sm",
        // red: no usage
        NO_USAGE: "bg-red-100 text-red-700 ring-1 ring-red-200 shadow-sm",
        // orange: low usage
        LOW: "bg-orange-100 text-orange-700 ring-1 ring-orange-200 shadow-sm",
        // amber: modderate usage
        MODERATE: "bg-yellow-100 text-yellow-700 ring-1 ring-yellow-200 shadow-sm",
        // lime: high usage 
        HIGH: "bg-lime-100 text-lime-700 ring-1 ring-lime-200 shadow-sm",
        // emerald: optimal usage
        VERY_HIGH: "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200 shadow-sm"
    };
    return colorMap[metric] || "bg-gray-400";
}

// Open employee modal
function openEmployeeModal(email) {
    const employee = employeesData.find(emp => emp.email === email);
    if (!employee) return;

    currentEmployee = employee;

    refreshMetricSelectOptions();

    document.getElementById('modalEmployeeName').textContent = employee.name;
    document.getElementById('modalEmployeeEmail').textContent = employee.email;
    document.getElementById('modalEmployeeRole').textContent = employee.role;
    document.getElementById('modalEmployeeTeam').textContent = employee.team;
    document.getElementById('modalEmployeeDate').textContent = employee.date;
    document.getElementById('modalEmployeeObservation').value = employee.observation || '';
    document.getElementById('modalMetricSelect').value = employee.metric;

    const modal = document.getElementById('employeeModal');
    modal.classList.remove('hidden');
}

// Close modal
function closeModal() {
    const modal = document.getElementById('employeeModal');
    modal.classList.add('hidden');
    currentEmployee = null;
}

// Save metric
function saveMetric() {
    if (!currentEmployee) return;

    const newMetric = document.getElementById('modalMetricSelect').value;
    const newObservation = document.getElementById('modalEmployeeObservation').value;

    // Find and update the employee in the data
    const employeeIndex = employeesData.findIndex(emp => emp.email === currentEmployee.email);
    if (employeeIndex !== -1) {
        employeesData[employeeIndex].metric = newMetric;
        employeesData[employeeIndex].observation = newObservation;
        persistEmployeesData();

        // Show success message
        showNotification(translate('notifications.metricSaved') || 'Metric updated successfully');

        // Re-render dashboard
        renderDashboard();

        // Close modal
        closeModal();
    }
}

// Add new entry
function addNewEntry() {
    if (!currentEmployee) return;

    // In a real application, this would open a form to add a new metric entry
    // For this demo, we'll just show a notification
    showNotification(translate('notifications.featureComingSoon') || 'Feature coming soon: Add new entry');
}

// Show notification
function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'fixed top-6 right-6 z-50 animate-slideIn bg-blue-50 text-blue-600 px-5 py-3 rounded-2xl shadow-lg border border-blue-100 font-semibold';
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }

    .animate-slideIn {
        animation: slideIn 0.3s ease;
    }
`;
document.head.appendChild(style);

// Utilities for dashboard rendering
function getEmployeesByDimension() {
    // if (currentDimension === 'genAIQA') {
    //     return employeesData.filter(emp => emp.role === 'QA');
    // }
    // return employeesData.filter(emp => emp.role !== 'QA');
    return employeesData;
}

function getUniqueRoles(list) {
    return [...new Set(list.map(emp => emp.role))];
}

function getUniqueTeams(list) {
    return [...new Set(list.map(emp => emp.team))];
}

function getEmployeesByRoleAndTeam(role, team, list) {
    return list.filter(emp => emp.role === role && emp.team === team);
}

function getInitials(name) {
    return name
        .split(' ')
        .filter(Boolean)
        .map(part => part[0])
        .join('')
        .slice(0, 3)
        .toUpperCase();
}

// Refresh modal metric options with dimension-specific labels
function refreshMetricSelectOptions() {
    const select = document.getElementById('modalMetricSelect');
    if (!select) return;

    select.innerHTML = '';

    METRIC_LEVELS.forEach(level => {
        const option = document.createElement('option');
        option.value = level;
        option.textContent = translate(`metricsDescriptions.${currentDimension}.${level}`) || level;
        select.appendChild(option);
    });

    if (currentEmployee && METRIC_LEVELS.includes(currentEmployee.metric)) {
        select.value = currentEmployee.metric;
    } else {
        select.value = 'UNDEFINED';
    }
}

// Export current dataset as downloadable JSON file
function exportCurrentData() {
    const blob = new Blob([JSON.stringify(employeesData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sinapxia-data.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
