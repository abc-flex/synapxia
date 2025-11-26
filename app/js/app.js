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

    let html = '<table class="grid-table"><thead><tr>';
    html += '<th class="role-header">Role / Team</th>';

    // Create team headers
    teams.forEach(team => {
        html += `<th>${team}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Create rows for each role
    roles.forEach(role => {
        html += '<tr>';
        html += `<td class="role-cell">${role}</td>`;

        // Create cells for each team
        teams.forEach(team => {
            const employees = getEmployeesByRoleAndTeam(role, team);
            html += '<td>';

            if (employees.length > 0) {
                html += '<div class="avatars-container">';
                employees.forEach(emp => {
                    const initials = getInitials(emp.name);
                    const metricClass = getMetricClass(emp.metric);
                    html += `
                        <div class="avatar ${metricClass}" 
                             onclick="openEmployeeModal('${emp.email}')"
                             title="${emp.name}">
                            ${initials}
                            <div class="avatar-tooltip">${emp.name}</div>
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
    modal.classList.add('active');
}

// Close modal
function closeModal() {
    const modal = document.getElementById('employeeModal');
    modal.classList.remove('active');
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
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #667eea;
        color: white;
        padding: 1rem 2rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
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
`;
document.head.appendChild(style);
