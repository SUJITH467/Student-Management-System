// Shared functions for dashboard and students page

// Determine API base dynamically: use global window.API_BASE if set,
// otherwise when developing on live-server (:5500) point to Flask (:5000),
// else use the same origin.
const API_BASE = window.API_BASE || ((window.location.port === '5500') ? 'http://127.0.0.1:5000' : window.location.origin);

async function apiFetch(url, opts = {}) {
  const fullUrl = (typeof url === 'string' && (url.startsWith('http://') || url.startsWith('https://'))) ? url : (API_BASE + url);
  const res = await fetch(fullUrl, Object.assign({
    headers: {
      "Content-Type": "application/json",
    },
  }, opts));
  let data;
  try {
    data = await res.json();
  } catch (e) {
    throw new Error("Invalid JSON response");
  }
  if (!res.ok) {
    const err = new Error(data.error || "Request failed");
    err.payload = data;
    throw err;
  }
  return data;
}

/* Dashboard */
async function loadDashboard() {
  try {
    const d = await apiFetch("/api/dashboard");
    document.getElementById("total-students").textContent = d.total_students;
    document.getElementById("total-courses").textContent = d.total_courses;
    document.getElementById("total-departments").textContent = d.total_departments;
  } catch (err) {
    console.error("Dashboard load error", err);
  }
}

/* Students page functions */
function attachStudentsPageHandlers() {
  const search = document.getElementById("search");
  const btnSearch = document.getElementById("btn-search");
  const btnRefresh = document.getElementById("btn-refresh");
  const btnOpenForm = document.getElementById("btn-open-form");
  const modal = document.getElementById("student-modal");
  const form = document.getElementById("student-form");
  const btnCancel = document.getElementById("form-cancel");

  if (btnSearch && search) btnSearch.addEventListener("click", () => loadStudents(search.value.trim()));
  if (btnRefresh && search) btnRefresh.addEventListener("click", () => { search.value=''; loadStudents(); });
  if (btnOpenForm) btnOpenForm.addEventListener("click", openAddForm);
  if (btnCancel) btnCancel.addEventListener("click", closeModal);
  if (form) form.addEventListener("submit", submitStudentForm);
}

async function loadDepartments() {
  try {
    const deps = await apiFetch("/api/departments");
    const sel = document.getElementById("department_id");
    if (!sel) return;
    sel.innerHTML = "";
    deps.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.textContent = d.name;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed loading departments", err);
  }
}

async function loadStudents(search = "") {
  try {
    const url = "/api/students" + (search ? "?search=" + encodeURIComponent(search) : "");
    const students = await apiFetch(url);
    const tbody = document.getElementById("students-body");
    tbody.innerHTML = "";
    if (students.length === 0) {
      tbody.innerHTML = "<tr><td colspan='11'>No students found.</td></tr>";
      return;
    }
    students.forEach(s => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${s.id}</td>
        <td>${escapeHtml(s.student_id || "")}</td>
        <td>${escapeHtml(s.full_name || "")}</td>
        <td>${escapeHtml(s.email || "")}</td>
        <td>${escapeHtml(s.phone || "")}</td>
        <td>${escapeHtml(s.department || "")}</td>
        <td>${escapeHtml(s.year || "")}</td>
        <td>${escapeHtml(s.student_type || "")}</td>
        <td>${escapeHtml(s.dob || "")}</td>
        <td>${escapeHtml(s.address || "")}</td>
        <td>
          <button class="btn btn-edit" onclick="openEditForm(${s.id})">Edit</button>
          <button class="btn btn-delete" onclick="deleteStudent(${s.id})">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading students", err);
    const tbody = document.getElementById("students-body");
    if (tbody) tbody.innerHTML = "<tr><td colspan='11'>Error loading students.</td></tr>";
  }
}

function escapeHtml(s) {
  if (!s && s !== 0) return "";
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* Modal and form */
function openAddForm() {
  resetForm();
  const modal = document.getElementById("student-modal");
  document.getElementById("modal-title").textContent = "Add Student";
  modal.setAttribute("aria-hidden", "false");
}

async function openEditForm(id) {
  try {
    const s = await apiFetch("/api/students/" + id);
    document.getElementById("student-db-id").value = s.id;
    document.getElementById("student_id").value = s.student_id || "";
    document.getElementById("full_name").value = s.full_name || "";
    document.getElementById("email").value = s.email || "";
    document.getElementById("phone").value = s.phone || "";
    document.getElementById("department_id").value = s.department_id || "";
    document.getElementById("year").value = s.year || "";
    document.getElementById("student_type").value = s.student_type || "College";
    document.getElementById("dob").value = s.dob || "";
    document.getElementById("address").value = s.address || "";

    document.getElementById("modal-title").textContent = "Edit Student";
    document.getElementById("student-modal").setAttribute("aria-hidden", "false");
  } catch (err) {
    alert("Failed to load student: " + (err.payload?.error || err.message));
  }
}

function closeModal() {
  const modal = document.getElementById("student-modal");
  if (modal) modal.setAttribute("aria-hidden", "true");
  resetForm();
}

function resetForm() {
  const form = document.getElementById("student-form");
  form.reset();
  document.getElementById("student-db-id").value = "";
  document.getElementById("student_type").value = "College";
  document.getElementById("modal-title").textContent = "Add Student";
}

async function submitStudentForm(e) {
  e.preventDefault();
  const dbId = document.getElementById("student-db-id").value;
  const payload = {
    student_id: document.getElementById("student_id").value.trim(),
    full_name: document.getElementById("full_name").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone: document.getElementById("phone").value.trim(),
    department_id: document.getElementById("department_id").value,
    year: document.getElementById("year").value,
    student_type: document.getElementById("student_type").value,
    dob: document.getElementById("dob").value,
    address: document.getElementById("address").value.trim(),
  };

  try {
    if (dbId) {
      await apiFetch("/api/students/" + dbId, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      alert("Student updated.");
    } else {
      await apiFetch("/api/students", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      alert("Student added.");
    }
    closeModal();
    loadStudents();
    loadDashboard();
  } catch (err) {
    console.error("Submit error", err);
    if (err.payload && err.payload.errors) {
      const errs = err.payload.errors;
      const msg = Object.values(errs).join("\n");
      alert("Validation errors:\n" + msg);
    } else {
      alert("Error: " + (err.payload?.error || err.message));
    }
  }
}

async function deleteStudent(id) {
  if (!confirm("Delete this student? This cannot be undone.")) return;
  try {
    await apiFetch("/api/students/" + id, { method: "DELETE" });
    alert("Deleted.");
    loadStudents();
    loadDashboard();
  } catch (err) {
    console.error("Delete error", err);
    alert("Failed to delete: " + (err.payload?.error || err.message));
  }
}

/* Attendance page functions */
function attachAttendancePageHandlers() {
  const btnOpenAttendance = document.getElementById("btn-open-attendance-form");
  const btnFilter = document.getElementById("btn-filter-attendance");
  const btnRefresh = document.getElementById("btn-refresh-attendance");
  const btnExport = document.getElementById("btn-export-attendance");
  const btnCancel = document.getElementById("attendance-cancel");
  const form = document.getElementById("attendance-form");

  if (btnOpenAttendance) btnOpenAttendance.addEventListener("click", openAttendanceForm);
  if (btnFilter) btnFilter.addEventListener("click", () => {
    const date = document.getElementById("attendance-date-filter").value;
    loadAttendance(date);
  });
  if (btnRefresh) btnRefresh.addEventListener("click", () => {
    document.getElementById("attendance-date-filter").value = "";
    loadAttendance();
  });
  if (btnExport) btnExport.addEventListener("click", exportAttendanceToSheet);
  if (btnCancel) btnCancel.addEventListener("click", closeAttendanceModal);
  if (form) form.addEventListener("submit", submitAttendanceForm);
}

async function loadAttendanceStudents() {
  try {
    const students = await apiFetch("/api/students");
    const sel = document.getElementById("attendance_student_id");
    if (!sel) return;
    sel.innerHTML = "";
    students.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.student_id} — ${s.full_name}`;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed loading attendance students", err);
  }
}

async function loadAttendance(date = "") {
  try {
    const url = "/api/attendance" + (date ? `?date=${encodeURIComponent(date)}` : "");
    const records = await apiFetch(url);
    const tbody = document.getElementById("attendance-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (records.length === 0) {
      tbody.innerHTML = "<tr><td colspan='6'>No attendance records found.</td></tr>";
      return;
    }
    records.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.id}</td>
        <td>${escapeHtml(r.student_name || "")}</td>
        <td>${escapeHtml(r.date || "")}</td>
        <td>${escapeHtml(r.status || "")}</td>
        <td>${escapeHtml(r.remarks || "")}</td>
        <td>
          <button class="btn btn-delete" onclick="deleteAttendance(${r.id})">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading attendance", err);
    const tbody = document.getElementById("attendance-body");
    if (tbody) tbody.innerHTML = "<tr><td colspan='6'>Error loading attendance.</td></tr>";
  }
}

function openAttendanceForm() {
  resetAttendanceForm();
  document.getElementById("attendance-modal").setAttribute("aria-hidden", "false");
}

function closeAttendanceModal() {
  const modal = document.getElementById("attendance-modal");
  if (modal) modal.setAttribute("aria-hidden", "true");
  resetAttendanceForm();
}

function resetAttendanceForm() {
  const form = document.getElementById("attendance-form");
  if (form) form.reset();
  document.getElementById("attendance-record-id").value = "";
  document.getElementById("attendance_status").value = "Present";
}

async function submitAttendanceForm(e) {
  e.preventDefault();
  const payload = {
    student_id: document.getElementById("attendance_student_id").value,
    date: document.getElementById("attendance_date").value,
    status: document.getElementById("attendance_status").value,
    remarks: document.getElementById("attendance_remarks").value.trim(),
  };

  try {
    await apiFetch("/api/attendance", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    alert("Attendance saved.");
    closeAttendanceModal();
    loadAttendance();
  } catch (err) {
    console.error("Submit attendance error", err);
    if (err.payload && err.payload.errors) {
      const msg = Object.values(err.payload.errors).join("\n");
      alert("Validation errors:\n" + msg);
    } else {
      alert("Error: " + (err.payload?.error || err.message));
    }
  }
}

async function exportAttendanceToSheet() {
  const status = document.getElementById("attendance-export-status");
  if (status) {
    status.textContent = "Exporting attendance to Google Sheets...";
  }
  try {
    const result = await apiFetch("/api/attendance/export", { method: "POST" });
    if (status) {
      status.textContent = result.message || "Export complete.";
    }
  } catch (err) {
    console.error("Export attendance error", err);
    if (status) {
      status.textContent = "Export failed: " + (err.payload?.error || err.message);
    }
  }
}

async function deleteAttendance(id) {
  if (!confirm("Delete this attendance record?")) return;
  try {
    await apiFetch("/api/attendance/" + id, { method: "DELETE" });
    loadAttendance();
  } catch (err) {
    console.error("Delete attendance error", err);
    alert("Failed to delete attendance: " + (err.payload?.error || err.message));
  }
}
