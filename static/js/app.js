const TABS = [
    { id: 'training', label: 'Progress', roles: ['athlete', 'trainer'] },
    { id: 'management', label: 'Management', roles: ['trainer'] },
    { id: 'medical', label: 'Medical', roles: ['medical'] },
    { id: 'enrollment', label: 'Enrollment', roles: ['athlete'] }
];

const savedUser = JSON.parse(localStorage.getItem("user"));

if (savedUser) {
    showDashboard(savedUser);
    toggleView('dashboard-view');
} else {
    toggleView('login-view');
}

function showSuccessMessage(title, message) {
    document.getElementById('success-title').innerText = title;
    document.getElementById('success-message').innerText = message;
    document.getElementById('success-modal').classList.remove('hidden');
}

function closeSuccessAndGoToLogin() {
    document.getElementById('success-modal').classList.add('hidden');
    document.getElementById('signup-view').classList.add('hidden');
    document.getElementById('login-view').classList.remove('hidden');
    document.getElementById('signup-form').reset();
}

function toggleAccordion(header) {
    const content = header.nextElementSibling;
    const isOpen = content.classList.contains('open');
    
    const parent = header.closest('#measurements, #measurements-medical');
    if (parent) {
        parent.querySelectorAll('.accordion-content').forEach(c => c.classList.remove('open'));
        parent.querySelectorAll('.accordion-header').forEach(h => h.classList.remove('active'));
    }
    
    if (!isOpen) {
        content.classList.add('open');
        header.classList.add('active');
    }
}

function toggleView(view_id) {
    const view = document.getElementById(view_id);
    if (view.classList.contains('hidden')) {
        view.classList.remove('hidden');
    } else {
        view.classList.add('hidden');
    }
}

const loginForm = document.getElementById('login-form');

async function get_user(login_email, login_password) {
    const result = await fetch("http://127.0.0.1:5000/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email: login_email,
            password: login_password
        })
    });

    if (!result.ok) {
        throw new Error("Login failed.")
    }
    return await result.json();
}

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const login_info = {
        login_email: document.getElementById('login-email').value,
        login_password: document.getElementById('login-password').value,
    };

    try {
        const user = await get_user(
            login_info.login_email,
            login_info.login_password
        );

        localStorage.setItem("user", JSON.stringify(user));
        toggleView('view-toggle-view');
        toggleView('login-view');
        toggleView('dashboard-view');
        showDashboard(user);
        console.log("User from backend:", user);
        console.log("Role:", user.role);

    } catch (err) {
        window.alert("Login failed");
        console.error(err);
    }
});

const signupForm = document.getElementById('signup-form');

signupForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const signup_info = {
        first_name: document.getElementById('first-name').value,
        last_name: document.getElementById('last-name').value,
        signup_email: document.getElementById('signup-email').value,
        signup_password: document.getElementById('signup-password').value,
        phone: document.getElementById('phone').value,
        gender: document.getElementById('gender').value,
        role: document.getElementById('role-select').value,
        date_of_birth: document.getElementById('date_of_birth').value
    }

    if (signup_info.role === "trainer") {
        signup_info.specialization = document.getElementById('specialization').value;
        signup_info.years_experience = document.getElementById('trainer-experience').value;
    } else if (signup_info.role === "athlete") {
        signup_info.sports_branch = document.getElementById('sports-branch').value;
    } else if (signup_info.role === "medical") {
        signup_info.profession = document.getElementById('profession').value;
        signup_info.specialization_area = document.getElementById('specialization-area').value;
    }

    fetch("http://127.0.0.1:5000/signup", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(signup_info)
    })
        .then(res => res.json())
        .then(data => {
            showSuccessMessage("Sign up successful!", "Your account has been created. Click below to log in.");
        });
})

function logout() {
    localStorage.removeItem('user');
    toggleView('dashboard-view');
    toggleView('login-view');
}

function showDashboard(user) {
    const role = user.role;
    const dashboardTitle = document.getElementById("dashboard-title");

    dashboardTitle.innerText = `Welcome, ${user["first_name"]}!`;

    const navMenu = document.getElementById('nav-menu');
    navMenu.innerHTML = '';
    let firstTabId = null;

    TABS.forEach(tab => {
        if (tab.roles.includes(role)) {

            const btn = document.createElement('button');
            btn.className = 'tab-btn';
            btn.innerText = tab.label;
            btn.onclick = () => switchTab(tab.id);
            navMenu.appendChild(btn);
            if (!firstTabId) firstTabId = tab.id;
        }
    });

    if (firstTabId) switchTab(firstTabId);
}

async function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(div => div.classList.add('hidden'));

    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    document.getElementById(`content-${tabId}`).classList.remove('hidden');

    const user = JSON.parse(localStorage.getItem("user"));


    if (user.role == "athlete" && tabId === "training") {
        const select = document.getElementById("athlete-select");
        select.classList.add('hidden');

        await loadAthletes("athlete-select");

        select.value = user.user_id;
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    if (user.role == "athlete" && tabId === "enrollment") {
        await loadEnrolledPrograms(user.user_id);
    }


    if (user.role == "trainer" && tabId === "training") {
        const select = document.getElementById("athlete-select");
        select.classList.remove('hidden');
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const clickedBtn = Array.from(document.querySelectorAll('.tab-btn'))
        .find(b => b.innerText === TABS.find(t => t.id === tabId).label);
    if (clickedBtn) clickedBtn.classList.add('active');
}

// Enrolled Programs dropdown for selected athlete
document.getElementById("athlete-select").addEventListener("change", async function () {
    const athleteId = this.value;
    const enrolledSelect = document.getElementById("enrolled-programs");

    enrolledSelect.innerHTML = '<option value="">No program selected</option>';

    if (!athleteId) return;

    try {   
        const res = await fetch(`/api/athletePrograms/${athleteId}`);
        if (!res.ok) return;
        const programs = await res.json();
        console.log('Enrolled programs:', programs);
        enrolledSelect.innerHTML = '<option value="">Select an enrolled program</option>';
        programs.forEach(p => {
            const option = document.createElement('option');
            option.value = p.id || p.program_id || '';
            option.textContent = `${p.name || p.program_name || 'Program'} — ${p.difficulty || p.difficulty_level || ''} (${p.start_date || ''} → ${p.end_date || ''})`;
            enrolledSelect.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load enrolled programs', err);
    }
});

const roleSelect = document.getElementById("role-select");
const roleFields = document.querySelectorAll(".role-fields");

roleSelect.addEventListener("change", function () {
    roleFields.forEach(div => div.style.display = "none");

    if (this.value) {
        document.getElementById(`${this.value}-fields`).style.display = "block";
    }
});

document.getElementById(`${roleSelect.value}-fields`).style.display = "block";

// Training Tab

// Load Athletes into dropdown
async function loadAthletes(id) {
    const result = await fetch("http://127.0.0.1:5000/api/athletes");
    const athletes = await result.json();

    const select = document.getElementById(id);
    select.innerHTML = '<option value="">Select an athlete</option>';

    athletes.forEach(a => {
        const option = document.createElement("option");
        option.value = a.id;
        option.textContent = a.id + ", " + a.name;
        select.appendChild(option);
    });
}


loadAthletes("athlete-select");

let measurementChart = null;
document.getElementById("athlete-select").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#measurementTable tbody");

    if (athleteId) {
        document.getElementById("measurements").classList.remove("hidden");
    } else {
        document.getElementById("measurements").classList.add("hidden");
    }

    tbody.innerHTML = "";

    if (measurementChart) {
        measurementChart.destroy();
        measurementChart = null;
    }

    if (!athleteId) return;

    const response = await fetch(`/api/measurements/${athleteId}`);
    const data = await response.json();

    const labels = [];
    const bmiData = [];
    const bodyFatData = [];
    const muscleMassData = [];

    data.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.measurement_date.split(":")[0].slice(0, -3)}</td>
            <td>${row.height}</td>
            <td>${row.weight}</td>
            <td>${row.body_fat_percentage}</td>
            <td>${row.muscle_mass}</td>
            <td>${row.bmi}</td>
        `;

        tbody.appendChild(tr);

        const date = new Date(row.measurement_date);
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const formattedDate = monthNames[date.getMonth()] + ' ' + String(date.getFullYear()).slice(-2);
        labels.push(formattedDate);
        bmiData.push(row.bmi);
        bodyFatData.push(row.body_fat_percentage);
        muscleMassData.push(row.muscle_mass);
    });

    if (data.length > 0) {
        const ctx = document.getElementById('measurementChart').getContext('2d');
        measurementChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels.reverse(),
                datasets: [
                    {
                        label: 'BMI',
                        data: bmiData.reverse(),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: false,
                        pointBackgroundColor: '#10b981',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Body Fat %',
                        data: bodyFatData.reverse(),
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: false,
                        pointBackgroundColor: '#3b82f6',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Muscle Mass (kg)',
                        data: muscleMassData.reverse(),
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: false,
                        pointBackgroundColor: '#f59e0b',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
});

// Medical Assessments Table
document.getElementById("athlete-select").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#medicalAssessment tbody");

    tbody.innerHTML = "";

    if (!athleteId) return;

    const response = await fetch(`/api/medicalAssessments/${athleteId}`);
    const data = await response.json();

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.doctor}</td>
            <td>${row.date.split(":")[0].slice(0, -3)}</td>
            <td>${row.type}</td>
            <td>${row.notes}</td>
            <td>${row.clearance}</td>
        `;
        tbody.appendChild(tr);
    });
});


// Last Training Logs Table
document.getElementById("athlete-select").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#lastTraining tbody");

    tbody.innerHTML = "";

    if (!athleteId) return;

    const response = await fetch(`/api/lastTraining/${athleteId}`);
    const data = await response.json();

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.exercise_name}</td>
            <td>${row.weight_used}</td>
            <td>${row.completed_sets}</td>
            <td>${row.completed_reps}</td>
            <td>${row.perceived_exertion}</td>
            <td>${row.log_time}</td>
        `;

        tbody.appendChild(tr);
    });
});

// Session Adherence Table
document.getElementById("athlete-select").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#sessionAdherence tbody");

    tbody.innerHTML = "";

    if (!athleteId) return;

    const response = await fetch(`/api/sessionAdherence/${athleteId}`);
    const data = await response.json();

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.percentage_sets_done}</td>
            <td>${row.percentage_reps_done}</td>
            <td>${row.average_rate_of_perceived_exertion}</td>
            <td>${row.session_date.split(":")[0].slice(0, -3)}</td>
        `;

        tbody.appendChild(tr);
    });
});

// Top Three Exercises Table
document.getElementById("athlete-select").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#top_three_exercises tbody");

    tbody.innerHTML = "";

    if (!athleteId) return;

    const response = await fetch(`/api/topThreeExercises/${athleteId}`);
    const data = await response.json();

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.rnk}</td>
            <td>${row.exercise_name}</td>
            <td>${row.total_volume}</td>
        `;

        tbody.appendChild(tr);
    });
});

// Submit Training Program (Management tab)
document.getElementById('create-program-btn').addEventListener('click', async (e) => {
    e.preventDefault();

    const name = document.getElementById('training_program_name').value.trim();
    const difficulty = document.getElementById('training_program_difficulty').value;
    const goal = document.getElementById('training_program_goal').value.trim();
    const start_date = document.getElementById('training_program_start_date').value;
    const end_date = document.getElementById('training_program_end_date').value;
    const trainer_id = savedUser.user_id;

    if (!name) {
        window.alert('Program name is required.');
        return;
    }

    const payload = {
        name,
        difficulty,
        goal,
        start_date,
        end_date,
        trainer_id
    };

    try {
        const res = await fetch('/api/createTrainingProgram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const data = await res.json().catch(() => ({}));
            window.alert(data.message || 'Training program created.');
            // clear form
            document.getElementById('training_program_name').value = '';
            document.getElementById('training_program_goal').value = '';
            document.getElementById('training_program_start_date').value = '';
            document.getElementById('training_program_end_date').value = '';
            document.getElementById('training_program_difficulty').value = 'beginner';
        } else {
            const err = await res.json().catch(() => ({}));
            window.alert(err.message || err.error || 'Failed to create program.');
        }
    } catch (err) {
        console.error(err);
        window.alert('Network error while creating program.');
    }
});


// Medical Tab
loadAthletes("athlete-select-medical")

// Measurements Table
document.getElementById("athlete-select-medical").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#measurementTable-medical tbody");

    if (athleteId) {
        document.getElementById("measurements-medical").classList.remove("hidden");
    } else {
        document.getElementById("measurements-medical").classList.add("hidden");
    }

    tbody.innerHTML = "";

    if (!athleteId) return;

    const response = await fetch(`/api/measurements/${athleteId}`);
    const data = await response.json();

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.measurement_date.split(":")[0].slice(0, -3)}</td>
            <td>${row.height}</td>
            <td>${row.weight}</td>
            <td>${row.body_fat_percentage}</td>
            <td>${row.muscle_mass}</td>
            <td>${row.bmi}</td>
        `;

        tbody.appendChild(tr);
    });
});

// Medical Assessments Table
document.getElementById("athlete-select-medical").addEventListener("change", async function () {
    const athleteId = this.value;
    const tbody = document.querySelector("#medicalAssessment-medical tbody");

    tbody.innerHTML = "";

    if (!athleteId) return;

    const response = await fetch(`/api/medicalAssessments/${athleteId}`);
    const data = await response.json();

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.doctor}</td>
            <td>${row.date.split(":")[0].slice(0, -3)}</td>
            <td>${row.type}</td>
            <td>${row.notes}</td>
            <td>${row.clearance}</td>
        `;

        tbody.appendChild(tr);
    });
});

// Submit Medical Exam
async function submitMedicalExam() {
    const type = document.getElementById("assessment_type").value;
    const exam_notes = document.getElementById("medical_exam_notes").value;
    const clearance = document.getElementById("clearance_status").value;

    const user = JSON.parse(localStorage.getItem("user"));
    const athlete = document.getElementById("athlete-select-medical").value;

    if (athlete) {
        const data = {
            athlete_id: athlete,
            medical_id: user["user_id"],
            assessment_type: type,
            notes: exam_notes,
            clearance_status: clearance
        }

        const response = await fetch("/api/addMedicalExam", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        alert(result.message);

        location.reload();
    } else {
        window.alert("Select an athlete first.")
    }

}

// Enrolled Programs dropdown data loading
async function loadEnrolledPrograms(athleteId) {
    const select = document.getElementById('enrollment-programs');
    if (!select) return;
    select.innerHTML = '<option value="">Loading...</option>';

    if (!athleteId) {
        select.innerHTML = '<option value="">No athlete selected</option>';
        return;
    }

    try {
        const res = await fetch(`/api/athletePrograms/${athleteId}`);
        if (!res.ok) {
            select.innerHTML = '<option value="">Failed to load</option>';
            return;
        }
        const programs = await res.json();
        if (!Array.isArray(programs) || programs.length === 0) {
            select.innerHTML = '<option value="">No enrolled programs</option>';
            return;
        }

        select.innerHTML = '<option value="">Select a program</option>';
        programs.forEach(p => {
            const id = p.program_id;
            const name = p.program_name;
            const start = p.start_date.split(":")[0].slice(0, -3);
            const end = p.end_date.split(":")[0].slice(0, -3);
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${name}: (${start} - ${end})`;
            select.appendChild(option);
        });
    } catch (err) {
        console.error(err);
        select.innerHTML = '<option value="">Error loading programs</option>';
    }
}

async function loadWorkoutSessions(programId) {
    const tbody = document.querySelector("#workout-sessions-container tbody");
    
    tbody.innerHTML = "";
    
    if (!programId) {
        return;
    }
    
    try {
        const res = await fetch(`/api/workoutSessions/${programId}`);
        if (!res.ok) {
            return;
        }
        
        const sessions = await res.json();
        if (!Array.isArray(sessions) || sessions.length === 0) {
            return;
        }
        
        sessions.forEach(s => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${s.session_date.split(":")[0].slice(0, -3)}</td>
                <td>${s.duration}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error(err);
    }
}

// New: Listen for program selection in enrollment tab
document.addEventListener('change', (e) => {
    if (e.target && e.target.id === 'enrollment-programs') {
        const programId = e.target.value;
        loadWorkoutSessions(programId);
    }
});

