// Data initialization - Converts CSV data to JSON structure
const employeesData = [
    {
        "name": "Roger Ricardo Roldan Bonilla",
        "email": "rrroldanb@ultragroupla.com",
        "role": "BACK",
        "team": "HADES",
        "metric": "Medio",
        "date": "15/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Oscar David Morales Ortiz",
        "email": "odmoraleso@ultragroupla.com",
        "role": "BACK",
        "team": "SKYNET",
        "metric": "Alto",
        "date": "16/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Angelo Nieto Triana",
        "email": "anietot@ultragroupla.com",
        "role": "BACK",
        "team": "SKYNET",
        "metric": "Medio",
        "date": "17/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Abel Jose Bautista Perez",
        "email": "ajbautistap@ultragroupla.com",
        "role": "BACK",
        "team": "SKYNET",
        "metric": "Alto",
        "date": "18/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Juan Carlos Gonzalez Sanchez",
        "email": "jcgonzalezs@ultragroupla.com",
        "role": "BACK",
        "team": "KEPLER",
        "metric": "Bajo",
        "date": "19/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Fernando Zapata Montes",
        "email": "fzapatam@ultragroupla.com",
        "role": "BACK",
        "team": "KEPLER",
        "metric": "Medio",
        "date": "20/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Alber Joanny Carmona Salazar",
        "email": "ajcarmonas@ultragroupla.com",
        "role": "BACK",
        "team": "KEPLER",
        "metric": "Medio",
        "date": "21/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Juan Esteban Alvarez Echavarria",
        "email": "jealvareze@ultragroupla.com",
        "role": "BACK",
        "team": "PIXEL",
        "metric": "Alto",
        "date": "22/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Cristian David Prada Suarez",
        "email": "cdpradas@ultragroupla.com",
        "role": "BACK",
        "team": "PIXEL",
        "metric": "Medio",
        "date": "23/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Cesar Luis Reyes Lopez",
        "email": "clreyesl@ultragroupla.com",
        "role": "BACK",
        "team": "PIXEL",
        "metric": "Medio",
        "date": "24/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Yeferson Yuberley Guerrero Castro",
        "email": "yyguerreroc@ultragroupla.com",
        "role": "BACK",
        "team": "ROCKET",
        "metric": "Bajo",
        "date": "25/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Hernando Jose Rumbo Nuñez",
        "email": "hjrumbon@ultragroupla.com",
        "role": "BACK",
        "team": "ROCKET",
        "metric": "Alto",
        "date": "26/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jorge Eliecer Tapias Higuita",
        "email": "jetapiash@ultragroupla.com",
        "role": "BACK",
        "team": "ROCKET",
        "metric": "Alto",
        "date": "27/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Cristian Gomez Florez",
        "email": "cgomezf@ultragroupla.com",
        "role": "FRONT",
        "team": "HADES",
        "metric": "Alto",
        "date": "28/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jhonatan Alberto Durango Rios",
        "email": "jadurangor@ultragroupla.com",
        "role": "FRONT",
        "team": "HADES",
        "metric": "Medio",
        "date": "29/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Luddy Mileny Puerta Ruiz",
        "email": "lmpuertar@ultragroupla.com",
        "role": "FRONT",
        "team": "SKYNET",
        "metric": "Medio",
        "date": "30/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Sergio Mauricio Pimiento Niño",
        "email": "smpimienton@ultragroupla.com",
        "role": "FRONT",
        "team": "SKYNET",
        "metric": "Bajo",
        "date": "31/01/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Ricardo Enrique Jaramillo Acevedo",
        "email": "rejaramilloa@ultragroupla.com",
        "role": "FRONT",
        "team": "SKYNET",
        "metric": "Alto",
        "date": "1/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Sergio Alejandro Riaño Acosta",
        "email": "sariañoa@ultragroupla.com",
        "role": "FRONT",
        "team": "KEPLER",
        "metric": "Alto",
        "date": "2/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Victor Alejandro Prada Noreña",
        "email": "vapradan@ultragroupla.com",
        "role": "FRONT",
        "team": "KEPLER",
        "metric": "Alto",
        "date": "3/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Cristhian David Velez Torres",
        "email": "cdvelezt@ultragroupla.com",
        "role": "FRONT",
        "team": "KEPLER",
        "metric": "Alto",
        "date": "4/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Robinson Betancur Marin",
        "email": "rbetancurm@ultragroupla.com",
        "role": "FRONT",
        "team": "PIXEL",
        "metric": "Bajo",
        "date": "5/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Andres Felipe Bolaños Ramirez",
        "email": "afbolañosr@ultragroupla.com",
        "role": "FRONT",
        "team": "PIXEL",
        "metric": "Alto",
        "date": "6/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Camila Espinosa Ramirez",
        "email": "cespinosar@ultragroupla.com",
        "role": "FRONT",
        "team": "ROCKET",
        "metric": "Medio",
        "date": "7/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jeyson Julian Ospina Leon",
        "email": "jjospinal@ultragroupla.com",
        "role": "FRONT",
        "team": "ROCKET",
        "metric": "Bajo",
        "date": "8/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Johan Sebastian Hidalgo Sandoval",
        "email": "jshidalgos@ultragroupla.com",
        "role": "FRONT",
        "team": "ROCKET",
        "metric": "Bajo",
        "date": "9/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Juan David Ceballos Ospina",
        "email": "jdceballoso@ultragroupla.com",
        "role": "QA",
        "team": "HADES",
        "metric": "Bajo",
        "date": "10/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Oswaldo Alzate Franco",
        "email": "oalzatef@ultragroupla.com",
        "role": "QA",
        "team": "HADES",
        "metric": "Bajo",
        "date": "11/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Andrea Estefania Mejia",
        "email": "aestefaniam@ultragroupla.com",
        "role": "QA",
        "team": "HADES",
        "metric": "Bajo",
        "date": "12/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jenny Marcela Florez Hinestroza",
        "email": "jmflorezh@ultragroupla.com",
        "role": "QA",
        "team": "SKYNET",
        "metric": "Bajo",
        "date": "13/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Carlos Alberto Rubio Gallego",
        "email": "carubiog@ultragroupla.com",
        "role": "QA",
        "team": "SKYNET",
        "metric": "Alto",
        "date": "14/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Natalia Gallego Rios",
        "email": "ngallegor@ultragroupla.com",
        "role": "QA",
        "team": "SKYNET",
        "metric": "Medio",
        "date": "15/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jose Eulises Barbosa Colorado",
        "email": "jebarbosac@ultragroupla.com",
        "role": "QA",
        "team": "KEPLER",
        "metric": "Alto",
        "date": "16/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jeferson Daniel Romero Acosta",
        "email": "jdromeroa@ultragroupla.com",
        "role": "QA",
        "team": "KEPLER",
        "metric": "Bajo",
        "date": "17/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Jesus Ernesto Marin Hernandez",
        "email": "jemarinh@ultragroupla.com",
        "role": "QA",
        "team": "KEPLER",
        "metric": "Alto",
        "date": "18/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Yhonatan Urrea Tascon",
        "email": "yurreat@ultragroupla.com",
        "role": "QA",
        "team": "PIXEL",
        "metric": "Bajo",
        "date": "19/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Camilo Pelaez Ramirez",
        "email": "cpelaezr@ultragroupla.com",
        "role": "QA",
        "team": "PIXEL",
        "metric": "Medio",
        "date": "20/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Andres Felipe Sanchez Quevedo",
        "email": "afsanchezq@ultragroupla.com",
        "role": "QA",
        "team": "PIXEL",
        "metric": "Alto",
        "date": "21/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Juan David Ceballos Cogollo",
        "email": "jdceballosc@ultragroupla.com",
        "role": "QA",
        "team": "ROCKET",
        "metric": "Medio",
        "date": "22/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Enma Del Carmen Gonzalez Sanchez",
        "email": "edcgonzalezs@ultragroupla.com",
        "role": "QA",
        "team": "ROCKET",
        "metric": "Bajo",
        "date": "23/02/2026",
        "observation": "Nivel de adopción de IA medio"
    },
    {
        "name": "Diego Fernando Castellanos Vargas",
        "email": "dfcastellanosv@ultragroupla.com",
        "role": "QA",
        "team": "ROCKET",
        "metric": "Alto",
        "date": "24/02/2026",
        "observation": "Nivel de adopción de IA medio"
    }
];

// Metric scale mapping
const metricScale = {
    "Alto": "High",
    "Medio": "Medium",
    "Bajo": "Low"
};

// Get unique roles and teams
function getUniqueRoles() {
    return [...new Set(employeesData.map(emp => emp.role))].sort();
}

function getUniqueTeams() {
    return [...new Set(employeesData.map(emp => emp.team))].sort();
}

// Get employees by role and team
function getEmployeesByRoleAndTeam(role, team) {
    return employeesData.filter(emp => emp.role === role && emp.team === team);
}

// Get initials from name
function getInitials(name) {
    const parts = name.split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

// Get metric class
function getMetricClass(metric) {
    const metricMap = {
        "Alto": "metric-high",
        "Medio": "metric-medium",
        "Bajo": "metric-low"
    };
    return metricMap[metric] || "metric-medium";
}
