// Application state
let currentDimension = 'aiAdoption';
let currentEmployee = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeI18n();
    renderDashboard();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Dimension selector
    const dimensionSelect = document.getElementById('dimensionSelect');
    dimensionSelect.addEventListener('change', (e) => {
        currentDimension = e.target.value;
        renderDashboard();
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
    });
}

// Render the dashboard grid
function renderDashboard() {
    const container = document.getElementById('dashboardGrid');
    const roles = getUniqueRoles();
    const teams = getUniqueTeams();

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
            const employees = getEmployeesByRoleAndTeam(role, team);
            html += '<td class="px-4 py-3 border border-gray-200 text-center">';

            if (employees.length > 0) {
                html += '<div class="flex flex-wrap gap-2 justify-center items-center min-h-[60px]">';
                employees.forEach(emp => {
                    const initials = getInitials(emp.name);
                    const metricClass = getMetricColorClass(emp.metric);
                    html += `
                        <div class="avatar w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm text-white cursor-pointer transition-transform hover:scale-110 shadow-md relative z-20 ${metricClass}" 
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
        "Alto": "bg-green-500 hover:bg-green-600",
        "Medio": "bg-amber-400 hover:bg-amber-500",
        "Bajo": "bg-red-500 hover:bg-red-600"
    };
    return colorMap[metric] || "bg-gray-400";
}

// Open employee modal
function openEmployeeModal(email) {
    const employee = employeesData.find(emp => emp.email === email);
    if (!employee) return;

    currentEmployee = employee;

    document.getElementById('modalEmployeeName').textContent = employee.name;
    document.getElementById('modalEmployeeEmail').textContent = employee.email;
    document.getElementById('modalEmployeeRole').textContent = employee.role;
    document.getElementById('modalEmployeeTeam').textContent = employee.team;
    document.getElementById('modalEmployeeDate').textContent = employee.date;
    document.getElementById('modalEmployeeObservation').textContent = employee.observation;
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

    // Find and update the employee in the data
    const employeeIndex = employeesData.findIndex(emp => emp.email === currentEmployee.email);
    if (employeeIndex !== -1) {
        employeesData[employeeIndex].metric = newMetric;

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
    notification.className = 'fixed top-6 right-6 bg-indigo-600 text-white px-8 py-4 rounded-lg shadow-lg z-50 animate-slideIn';
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
