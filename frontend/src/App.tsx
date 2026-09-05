import { useEffect, useMemo, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import "./App.css";

type Role = "TUTOR" | "STUDENT";
type SessionStatus = "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "AI_REVIEWED";

type Student = {
  id: string;
  user_id: string;
  tutor_id: string;
  name?: string | null;
  email?: string;
  learning_goals?: string | null;
  skill_level?: string | null;
  preferences?: string | null;
  created_at?: string;
};

type Session = {
  id: string;
  tutor_id: string;
  student_id: string;
  start_time: string;
  end_time: string;
  status: SessionStatus;
  notes?: string | null;
  homework?: string | null;
  ai_plan?: string | null;
  ai_summary?: string | null;
  created_at: string;
  updated_at: string;
  student_name?: string | null;
  tutor_name?: string | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function parseRoleFromToken(token: string | null): Role | null {
  if (!token) return null;
  try {
    const segments = token.split(".");
    if (segments.length < 2) return null;
    const base64 = segments[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded));
    return payload.role;
  } catch {
    return null;
  }
}

function getDashboardPath(role: Role | null) {
  if (role === "TUTOR") return "/dashboard";
  if (role === "STUDENT") return "/student/dashboard";
  return "/login";
}

function getToken() {
  return localStorage.getItem("tutorflow_token");
}

function setToken(token: string | null) {
  if (token) localStorage.setItem("tutorflow_token", token);
  else localStorage.removeItem("tutorflow_token");
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail ?? JSON.stringify(payload);
    } catch {
      try {
        message = await response.text();
      } catch {
        message = "Request failed";
      }
    }

    const error = new Error(message) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }

  return response;
}

function isNotFoundLikeError(error: unknown) {
  if (!(error instanceof Error)) return false;

  const status = (error as Error & { status?: number }).status;
  if (status === 403 || status === 404) return true;

  const normalized = error.message.toLowerCase();
  return normalized.includes("not found") || normalized.includes("forbidden");
}

function parseJsonField(raw: string | null | undefined) {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

const IST_TIMEZONE = "Asia/Kolkata";

function parseApiDate(value: string) {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`);
}

function formatDateTime(value: string) {
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIMEZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatShortId(value: string | null | undefined, fallback = "N/A") {
  if (!value) return fallback;
  return value.slice(0, 8).toUpperCase();
}

function getSessionPersonLabel(session: Session, role: Role, students: Student[] = []) {
  if (role === "TUTOR") {
    const student = students.find((item) => item.user_id === session.student_id);
    return session.student_name || formatStudentLabel(student);
  }
  return session.tutor_name || "Your tutor";
}

function formatStatusLabel(status: SessionStatus) {
  const labels: Record<SessionStatus, string> = {
    SCHEDULED: "Scheduled",
    IN_PROGRESS: "In Progress",
    COMPLETED: "Completed",
    AI_REVIEWED: "AI Reviewed",
  };
  return labels[status] ?? status;
}

function formatStudentLabel(student: Student | null | undefined) {
  if (!student) return "Unknown student";
  return student.name || student.email || `Student ${formatShortId(student.user_id, "Unknown")}`;
}

function formatSessionTime(session: Session) {
  const end = parseApiDate(session.end_time);
  const hasEnded = session.status === "IN_PROGRESS" && end.getTime() < Date.now();
  if (hasEnded) return `Scheduled end: ${formatDateTime(session.end_time)}`;
  return `${formatDateTime(session.start_time)} → ${formatDateTime(session.end_time)}`;
}

const lifecycleStatuses: SessionStatus[] = ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "AI_REVIEWED"];

function LifecycleStepper({ status }: { status: SessionStatus }) {
  const currentIndex = lifecycleStatuses.indexOf(status);
  return (
    <div className="lifecycle-stepper" aria-label={`Session lifecycle: ${formatStatusLabel(status)}`}>
      {lifecycleStatuses.map((step, index) => (
        <div key={step} className={`lifecycle-step ${index < currentIndex ? "done" : ""} ${index === currentIndex ? "current" : ""}`}>
          <span className="lifecycle-dot">{index < currentIndex ? "✓" : index + 1}</span>
          <span>{formatStatusLabel(step)}</span>
        </div>
      ))}
    </div>
  );
}

function renderAiContent(title: string, raw: string | null | undefined, fields: string[]) {
  const content = parseJsonField(raw);
  if (!content) return null;
  if (typeof content === "string") return <div className="info-block"><h3>{title}</h3><p>{content}</p></div>;
  return (
    <div className="info-block">
      <h3>{title}</h3>
      {fields.map((field) => {
        const value = content[field];
        const label = field.replace(/_/g, " ").replace(/^./, (letter: string) => letter.toUpperCase());
        return <p key={field}><strong>{label}:</strong> {Array.isArray(value) ? value.join(", ") : value || "Not specified"}</p>;
      })}
    </div>
  );
}

function getActionError(error: unknown, fallback: string) {
  if (!(error instanceof Error)) return fallback;
  const typed = error as Error & { status?: number };
  if (typed.status !== 409) return error.message || fallback;
  const times = error.message.match(/\d{4}-\d{2}-\d{2}T[^\s,]+/g) ?? [];
  if (times.length >= 2) {
    return `You already have a session scheduled for ${formatDateTime(times[0] ?? "")} → ${formatDateTime(times[1] ?? "")}. Choose another time.`;
  }
  return `You already have a session at the conflicting time. Choose another time.`;
}

function sortSessions(sessions: Session[]) {
  return [...sessions].sort(
    (a, b) => parseApiDate(a.start_time).getTime() - parseApiDate(b.start_time).getTime(),
  );
}

function ProtectedRoute({ requiredRole, children }: { requiredRole: Role; children: React.ReactNode }) {
  const token = getToken();
  const currentRole = parseRoleFromToken(token);
  const location = useLocation();

  if (!token || !currentRole) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (currentRole !== requiredRole) {
    return <Navigate to={getDashboardPath(currentRole)} replace />;
  }

  return <>{children}</>;
}

function AppLayout({ title, children, actions }: { title: string; children: React.ReactNode; actions?: React.ReactNode }) {
  const token = getToken();
  const navigate = useNavigate();
  const role = parseRoleFromToken(token);

  const handleLogout = () => {
    setToken(null);
    navigate("/login");
  };

  const navLinks =
    role === "STUDENT" ? (
      <>
        <Link to="/student/dashboard">Dashboard</Link>
        <Link to="/student/history">History</Link>
      </>
    ) : (
      <>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/students">Students</Link>
      </>
    );

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <Link to={getDashboardPath(role)} className="brand-link">TutorFlow</Link>
        </div>
        <nav className="topbar-nav">
          {navLinks}
          {token ? (
            <button type="button" className="ghost-button" onClick={handleLogout}>
              Logout
            </button>
          ) : null}
        </nav>
      </header>
      <main className="content-shell">
        <div className="panel">
          <div className="panel-header">
            <h1>{title}</h1>
            {actions}
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

function LoginPage() {
  const navigate = useNavigate();
  const [showTutorSignup, setShowTutorSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = getToken();
    const currentRole = parseRoleFromToken(token);
    if (token && currentRole) {
      navigate(getDashboardPath(currentRole), { replace: true });
    }
  }, [navigate]);

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      const currentRole = parseRoleFromToken(data.access_token);
      setToken(data.access_token);
      navigate(getDashboardPath(currentRole), { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleTutorSignup = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      setLoading(false);
      return;
    }

    try {
      await apiFetch("/auth/register-tutor", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setMessage("Tutor account created. You can now sign in.");
      setShowTutorSignup(false);
      setEmail("");
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tutor signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>TutorFlow</h1>
        <p>Learning sessions with clear scheduling and AI support</p>

        {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
        {message ? <div className="success-banner">{message}</div> : null}

        {showTutorSignup ? (
          <form onSubmit={handleTutorSignup} className="stacked-form">
            <label>
              Tutor email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label>
              Password
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            <label>
              Confirm password
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Creating account..." : "Create tutor account"}
            </button>
            <button type="button" className="ghost-button" onClick={() => setShowTutorSignup(false)}>
              Back to login
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin} className="stacked-form">
            <label>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label>
              Password
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Login"}
            </button>
            <button type="button" className="ghost-button" onClick={() => {
              setShowTutorSignup(true);
              setError("");
              setMessage("");
            }}>
              Create tutor account
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function TutorDashboard() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch("/sessions");
        const data: Session[] = await response.json();
        setSessions(sortSessions(data));
        const studentsResponse = await apiFetch("/students");
        setStudents(await studentsResponse.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load sessions");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const scheduled = useMemo(() => sessions.filter((session) => session.status === "SCHEDULED"), [sessions]);
  const inProgress = useMemo(() => sessions.filter((session) => session.status === "IN_PROGRESS"), [sessions]);

  return (
    <AppLayout title="Tutor Dashboard" actions={<Link to="/sessions/new" className="primary-link">Schedule Session</Link>}>
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      {loading ? <p>Loading...</p> : null}
      <div className="section-header">
        <h2>Scheduled sessions</h2>
        <Link to="/students">Manage students</Link>
      </div>
      {!loading && scheduled.length === 0 ? <p className="empty-state">No scheduled sessions - you&apos;re all caught up.</p> : null}
      <div className="card-list">
        {scheduled.map((session) => (
          <Link key={session.id} to={`/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{getSessionPersonLabel(session, "TUTOR", students)}</strong>
              <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
            </div>
            <div><strong>Time:</strong> {formatSessionTime(session)}</div>
          </Link>
        ))}
      </div>
      <div className="section-header"><h2>In-progress sessions</h2></div>
      {!loading && inProgress.length === 0 ? <p className="empty-state">No sessions are currently in progress.</p> : null}
      <div className="card-list">
        {inProgress.map((session) => (
          <Link key={session.id} to={`/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{getSessionPersonLabel(session, "TUTOR", students)}</strong>
              <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
            </div>
            <div><strong>Time:</strong> {formatSessionTime(session)}</div>
          </Link>
        ))}
      </div>
    </AppLayout>
  );
}

function StudentListPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createdStudent, setCreatedStudent] = useState<{ email: string; password: string } | null>(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    initial_password: "",
    learning_goals: "",
    skill_level: "",
    preferences: "",
  });

  useEffect(() => {
    const loadStudents = async () => {
      try {
        const response = await apiFetch("/students");
        setStudents(await response.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load students");
      } finally {
        setLoading(false);
      }
    };
    loadStudents();
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const response = await apiFetch("/students", {
        method: "POST",
        body: JSON.stringify(form),
      });
      const created = await response.json();
      setStudents((current) => [...current, created]);
      setCreatedStudent({
        email: form.email,
        password: form.initial_password,
      });
      setForm({ name: "", email: "", initial_password: "", learning_goals: "", skill_level: "", preferences: "" });
      setShowForm(false);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create student");
    }
  };

  return (
    <AppLayout title="Students">
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      {createdStudent ? (
        <div className="success-banner" data-testid="credential-panel">
          <strong>Student created.</strong>
          <div>Email: {createdStudent.email}</div>
          <div>Temporary password: {createdStudent.password}</div>
        </div>
      ) : null}
      <div className="section-header">
        <h2>My students</h2>
        <button type="button" onClick={() => setShowForm((value) => !value)}>
          {showForm ? "Cancel" : "Add Student"}
        </button>
      </div>
      {showForm ? (
        <form onSubmit={handleSubmit} className="stacked-form form-card">
          <label>
            Name
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Email
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label>
            Initial password
            <input type="text" value={form.initial_password} onChange={(e) => setForm({ ...form, initial_password: e.target.value })} required />
          </label>
          <label>
            Learning goals
            <textarea value={form.learning_goals} onChange={(e) => setForm({ ...form, learning_goals: e.target.value })} />
          </label>
          <label>
            Skill level
            <input type="text" value={form.skill_level} onChange={(e) => setForm({ ...form, skill_level: e.target.value })} />
          </label>
          <label>
            Preferences
            <textarea value={form.preferences} onChange={(e) => setForm({ ...form, preferences: e.target.value })} />
          </label>
          <button type="submit">Create student</button>
        </form>
      ) : null}
      {loading ? <p>Loading...</p> : null}
      <div className="card-list">
        {students.map((student) => (
          <Link key={student.id} to={`/students/${student.id}`} className="student-card">
            <div className="row-between">
              <strong>{formatStudentLabel(student)}</strong>
              <span>{student.skill_level ?? "No level"}</span>
            </div>
            <div>{student.learning_goals || "No learning goals provided"}</div>
          </Link>
        ))}
      </div>
    </AppLayout>
  );
}

function StudentDetailPage() {
  const { studentId } = useParams();
  const [student, setStudent] = useState<Student | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [nameDraft, setNameDraft] = useState("");
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (!studentId) return;
      try {
        const studentResponse = await apiFetch(`/students/${studentId}`);
        const studentData = await studentResponse.json();
        setStudent(studentData);
        setNameDraft(studentData.name ?? "");

        const sessionsResponse = await apiFetch("/sessions");
        const sessionData: Session[] = await sessionsResponse.json();
        setSessions(sortSessions(sessionData.filter((item) => item.student_id === studentData.user_id)));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load student detail");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [studentId]);

  if (loading) return <AppLayout title="Student detail"><p>Loading...</p></AppLayout>;
  if (!student) {
    return (
      <AppLayout title="Student detail">
        <div className="error-banner" data-testid="error-message">{error || "Student not found."}</div>
      </AppLayout>
    );
  }

  const handleSaveStudent = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const response = await apiFetch(`/students/${student.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: nameDraft }),
      });
      setStudent(await response.json());
      setEditMode(false);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update student");
    }
  };

  return (
    <AppLayout
      title={student.email ?? "Student details"}
      actions={<Link to={`/sessions/new?studentId=${student.user_id}`} className="primary-link">Schedule session</Link>}
    >
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      <div className="profile-grid">
        <div>
          <p><strong>Student:</strong> {formatStudentLabel(student)}</p>
          <p><strong>Student ID:</strong> {formatShortId(student.user_id, "Unknown")}</p>
          <p><strong>Email:</strong> {student.email}</p>
          <p><strong>Skill level:</strong> {student.skill_level || "Not specified"}</p>
          <p><strong>Learning goals:</strong> {student.learning_goals || "Not specified"}</p>
          <p><strong>Preferences:</strong> {student.preferences || "Not specified"}</p>
        </div>
      </div>
      {editMode ? (
        <form onSubmit={handleSaveStudent} className="stacked-form form-card">
          <label>
            Name
            <input data-testid="student-name-input" value={nameDraft} onChange={(event) => setNameDraft(event.target.value)} required />
          </label>
          <button type="submit" data-testid="save-student-btn">Save student</button>
        </form>
      ) : (
        <button type="button" onClick={() => setEditMode(true)}>Edit student</button>
      )}

      <h2>Session history</h2>
      {sessions.length === 0 ? <p>No sessions.</p> : null}
      <div className="card-list">
        {sessions.map((session) => (
          <Link key={session.id} to={`/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{getSessionPersonLabel(session, "TUTOR", [student])}</strong>
              <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
            </div>
            <div><strong>Time:</strong> {formatSessionTime(session)}</div>
          </Link>
        ))}
      </div>
    </AppLayout>
  );
}

function NewSessionPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [students, setStudents] = useState<Student[]>([]);
  const [studentId, setStudentId] = useState(searchParams.get("studentId") ?? "");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch("/students");
        const data: Student[] = await response.json();
        setStudents(data);
        if (!studentId && data[0]) {
          setStudentId(data[0].user_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load students");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");

    if (!studentId || !startTime || !endTime) {
      setError("Please select a student and session times.");
      return;
    }

    try {
      const response = await apiFetch("/sessions", {
        method: "POST",
        body: JSON.stringify({
          student_id: studentId,
          start_time: new Date(startTime).toISOString(),
          end_time: new Date(endTime).toISOString(),
        }),
      });
      const created: Session = await response.json();
      navigate(`/sessions/${created.id}`);
    } catch (err) {
      setError(getActionError(err, "Unable to create session"));
    }
  };

  return (
    <AppLayout title="Schedule session">
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      {loading ? <p>Loading students...</p> : (
        <form onSubmit={handleSubmit} className="stacked-form form-card">
          <label>
            Student
            <select value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
              {students.map((student) => (
                <option key={student.user_id} value={student.user_id}>{formatStudentLabel(student)}</option>
              ))}
            </select>
          </label>
          <label>
            Start time
            <input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
          </label>
          <label>
            End time
            <input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
          </label>
          <button type="submit">Create session</button>
        </form>
      )}
    </AppLayout>
  );
}

function StudentDashboard() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch("/sessions");
        const data: Session[] = await response.json();
        setSessions(sortSessions(data));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load your sessions");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const scheduled = useMemo(() => sessions.filter((session) => session.status === "SCHEDULED"), [sessions]);
  const inProgress = useMemo(() => sessions.filter((session) => session.status === "IN_PROGRESS"), [sessions]);

  return (
    <AppLayout title="Student Dashboard">
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      {loading ? <p>Loading...</p> : null}
      {!loading && scheduled.length === 0 && inProgress.length === 0 ? <p className="empty-state">No upcoming sessions - you&apos;re all caught up.</p> : null}
      {scheduled.length > 0 ? <h2>Scheduled sessions</h2> : null}
      <div className="card-list">
        {scheduled.map((session) => (
          <Link key={session.id} to={`/student/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{getSessionPersonLabel(session, "STUDENT")}</strong>
              <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
            </div>
            <div><strong>Time:</strong> {formatSessionTime(session)}</div>
          </Link>
        ))}
      </div>
      {inProgress.length > 0 ? <h2>In-progress sessions</h2> : null}
      <div className="card-list">
        {inProgress.map((session) => (
          <Link key={session.id} to={`/student/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{getSessionPersonLabel(session, "STUDENT")}</strong>
              <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
            </div>
            <div><strong>Time:</strong> {formatSessionTime(session)}</div>
          </Link>
        ))}
      </div>
    </AppLayout>
  );
}

function StudentHistoryPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch("/sessions");
        const data: Session[] = await response.json();
        setSessions(
          sortSessions(
            data.filter((session) => session.status === "COMPLETED" || session.status === "AI_REVIEWED"),
          ),
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load your history");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  return (
    <AppLayout title="Session History">
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      {loading ? <p>Loading...</p> : null}
      {!loading && sessions.length === 0 ? <p>No past sessions yet.</p> : null}
      <div className="card-list">
        {sessions.map((session) => (
          <Link key={session.id} to={`/student/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{getSessionPersonLabel(session, "STUDENT")}</strong>
              <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
            </div>
            <div><strong>Time:</strong> {formatSessionTime(session)}</div>
          </Link>
        ))}
      </div>
    </AppLayout>
  );
}

function StudentSessionDetailPage() {
  const { sessionId } = useParams();
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSession = async () => {
      if (!sessionId) return;

      try {
        const response = await apiFetch(`/sessions/${sessionId}`);
        const data: Session = await response.json();
        setSession(data);
        setError("");
      } catch (err) {
        if (isNotFoundLikeError(err)) {
          setSession(null);
          setError("This session could not be found or is not available to you.");
        } else {
          setError(err instanceof Error ? err.message : "Unable to load session");
        }
      } finally {
        setLoading(false);
      }
    };

    loadSession();
  }, [sessionId]);

  if (loading) return <AppLayout title="Session details"><p>Loading...</p></AppLayout>;

  if (!session) {
    return (
      <AppLayout title="Session not found" actions={<Link to="/student/dashboard" className="primary-link">Back to dashboard</Link>}>
        <div className="error-banner" data-testid="error-message">{error || "This session could not be found or is not available to you."}</div>
      </AppLayout>
    );
  }

  const aiSummary = parseJsonField(session.ai_summary);

  return (
    <AppLayout title={getSessionPersonLabel(session, "STUDENT")} actions={<Link to="/student/dashboard" className="primary-link">Back to dashboard</Link>}>
      <div className="session-meta">
        <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
        <span><strong>Time:</strong> {formatSessionTime(session)}</span>
      </div>
      <LifecycleStepper status={session.status} />

      <div className="stacked-form form-card">
        <label>
          Notes
          <small>Notes capture what you worked on and what to revisit.</small>
          <textarea value={session.notes ?? ""} readOnly rows={6} />
        </label>
        <label>
          Homework
          <small>Homework records practice to complete before the next session.</small>
          <textarea value={session.homework ?? ""} readOnly rows={4} />
        </label>
      </div>

      {session.ai_plan ? renderAiContent("AI Plan", session.ai_plan, ["warm_up", "main_focus", "practice_activities", "check_for_understanding"]) : null}
      {session.ai_summary && aiSummary ? renderAiContent("AI Summary", session.ai_summary, ["summary", "strengths", "areas_to_improve", "recommended_next_topic"]) : null}

      {!session.notes && !session.homework && session.status !== "AI_REVIEWED" ? (
        <p>No notes or homework are available for this session yet.</p>
      ) : null}
    </AppLayout>
  );
}

function SessionDetailPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [homeworkDraft, setHomeworkDraft] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [rescheduleMode, setRescheduleMode] = useState(false);
  const [rescheduleStart, setRescheduleStart] = useState("");
  const [rescheduleEnd, setRescheduleEnd] = useState("");
  const [students, setStudents] = useState<Student[]>([]);
  const [savingNotes, setSavingNotes] = useState(false);
  const [notesSaved, setNotesSaved] = useState(false);
  const [aiError, setAiError] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  const loadSession = async () => {
    if (!sessionId) return;
    try {
      const response = await apiFetch(`/sessions/${sessionId}`);
      const data: Session = await response.json();
      setSession(data);
      setNotesDraft(data.notes ?? "");
      setHomeworkDraft(data.homework ?? "");
      setError("");
      try {
        const studentsResponse = await apiFetch("/students");
        setStudents(await studentsResponse.json());
      } catch {
        // Session data remains usable if the roster request is unavailable.
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load session");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSession();
  }, [sessionId]);

  const handleStart = async () => {
    try {
      const response = await apiFetch(`/sessions/${sessionId}/start`, {
        method: "PATCH",
        body: JSON.stringify({}),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start session");
    }
  };

  const handleReschedule = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const response = await apiFetch(`/sessions/${sessionId}/reschedule`, {
        method: "PATCH",
        body: JSON.stringify({
          start_time: new Date(rescheduleStart).toISOString(),
          end_time: new Date(rescheduleEnd).toISOString(),
        }),
      });
      setSession(await response.json());
      setRescheduleMode(false);
      setError("");
    } catch (err) {
      setError(getActionError(err, "Unable to reschedule session"));
    }
  };

  const handleCancel = async () => {
    try {
      await apiFetch(`/sessions/${sessionId}`, { method: "DELETE" });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to cancel session");
    }
  };

  const handleGeneratePlan = async () => {
    if (!session) return;
    const durationMinutes = Math.max(
      1,
      Math.round((parseApiDate(session.end_time).getTime() - parseApiDate(session.start_time).getTime()) / 60000),
    );

    try {
      setAiLoading(true);
      setAiError("");
      const response = await apiFetch(`/sessions/${session.id}/ai-plan`, {
        method: "POST",
        body: JSON.stringify({ duration_minutes: durationMinutes }),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setAiError("Couldn't generate this - your session data is safe.");
    } finally {
      setAiLoading(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!session) return;
    try {
      setSavingNotes(true);
      setNotesSaved(false);
      const response = await apiFetch(`/sessions/${session.id}/notes`, {
        method: "PATCH",
        body: JSON.stringify({ notes: notesDraft }),
      });
      const data: Session = await response.json();
      setSession(data);
      setNotesSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save notes");
    } finally {
      setSavingNotes(false);
    }
  };

  const handleComplete = async () => {
    if (!session) return;
    try {
      const response = await apiFetch(`/sessions/${session.id}/complete`, {
        method: "PATCH",
        body: JSON.stringify({ notes: notesDraft, homework: homeworkDraft }),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to complete session");
    }
  };

  const handleTriggerAiReview = async () => {
    if (!session) return;
    try {
      setAiLoading(true);
      setAiError("");
      const response = await apiFetch(`/sessions/${session.id}/trigger-ai-review`, {
        method: "PATCH",
        body: JSON.stringify({}),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setAiError("Couldn't generate this - your session data is safe.");
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) return <AppLayout title="Session detail"><p>Loading...</p></AppLayout>;
  if (!session) {
    return (
      <AppLayout title="Session detail">
        <div className="error-banner" data-testid="error-message">{error || "Session not found."}</div>
      </AppLayout>
    );
  }

  const aiPlan = parseJsonField(session.ai_plan);
  const aiSummary = parseJsonField(session.ai_summary);
  const isCompleteReady = notesDraft.trim().length > 0 && homeworkDraft.trim().length > 0;

  return (
    <AppLayout title={getSessionPersonLabel(session, "TUTOR", students)} actions={<button type="button" onClick={() => navigate("/dashboard")}>Back to dashboard</button>}>
      {error ? <div className="error-banner" data-testid="error-message">{error}</div> : null}
      {aiError ? <div className="error-banner" data-testid="ai-error">{aiError} <button type="button" className="inline-action" onClick={session.status === "COMPLETED" ? handleTriggerAiReview : handleGeneratePlan}>Try Again</button></div> : null}
      <div className="session-meta">
        <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
        <span><strong>Time:</strong> {formatSessionTime(session)}</span>
      </div>
      <LifecycleStepper status={session.status} />

      {session.status === "SCHEDULED" ? (
        <div className="action-row">
          {!session.ai_plan ? <button type="button" onClick={handleGeneratePlan} disabled={aiLoading}>{aiLoading ? "Generating plan..." : "Generate AI Plan"}</button> : null}
          <button type="button" data-testid="start-btn" onClick={handleStart}>Start Session</button>
          <button type="button" data-testid="reschedule-btn" onClick={() => setRescheduleMode((value) => !value)}>Reschedule</button>
          <button type="button" data-testid="cancel-btn" onClick={handleCancel}>Cancel session</button>
        </div>
      ) : null}

      {session.status === "SCHEDULED" && rescheduleMode ? (
        <form onSubmit={handleReschedule} className="stacked-form form-card">
          <label>
            Start time
            <input data-testid="reschedule-start-input" type="datetime-local" value={rescheduleStart} onChange={(event) => setRescheduleStart(event.target.value)} required />
          </label>
          <label>
            End time
            <input data-testid="reschedule-end-input" type="datetime-local" value={rescheduleEnd} onChange={(event) => setRescheduleEnd(event.target.value)} required />
          </label>
          <button type="submit" data-testid="reschedule-submit-btn">Save reschedule</button>
        </form>
      ) : null}

      {session.status === "IN_PROGRESS" ? (
        <div className="stacked-form form-card">
          <label>
            Notes
            <small>Use notes for what you worked on and what to revisit.</small>
            <textarea value={notesDraft} onChange={(e) => setNotesDraft(e.target.value)} rows={6} />
          </label>
          <label>
            Homework
            <small>Use homework for practice the student should complete next.</small>
            <textarea value={homeworkDraft} onChange={(e) => setHomeworkDraft(e.target.value)} rows={4} />
          </label>
          <div className="action-row">
            <button type="button" className="secondary-button" onClick={handleSaveNotes} disabled={savingNotes}>{savingNotes ? "Saving..." : "Save notes"}</button>
            {notesSaved ? <span className="save-state">Saved</span> : null}
            <button type="button" onClick={handleComplete} disabled={!isCompleteReady}>Complete Session</button>
          </div>
        </div>
      ) : (
        <div className="stacked-form form-card">
          <label>
            Notes
            <textarea value={notesDraft} readOnly rows={6} />
          </label>
          <label>
            Homework
            <textarea value={homeworkDraft} readOnly rows={4} />
          </label>
        </div>
      )}

      {session.status === "COMPLETED" ? (
        <div className="action-row">
          <button type="button" onClick={handleTriggerAiReview} disabled={aiLoading}>{aiLoading ? "Generating review..." : "Trigger AI Review"}</button>
        </div>
      ) : null}

      {session.status === "SCHEDULED" || session.status === "IN_PROGRESS" || session.status === "COMPLETED" ? (
        <div className="info-block">
          <h3>Session details</h3>
          {session.notes ? <p><strong>Notes:</strong> {session.notes}</p> : <p>No notes yet.</p>}
          {session.homework ? <p><strong>Homework:</strong> {session.homework}</p> : <p>No homework assigned yet.</p>}
        </div>
      ) : null}

      {aiPlan ? renderAiContent("AI Plan", session.ai_plan, ["warm_up", "main_focus", "practice_activities", "check_for_understanding"]) : null}
      {aiSummary ? renderAiContent("AI Summary", session.ai_summary, ["summary", "strengths", "areas_to_improve", "recommended_next_topic"]) : null}
    </AppLayout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Navigate to={getDashboardPath(parseRoleFromToken(getToken()))} replace />} />
      <Route path="/dashboard" element={<ProtectedRoute requiredRole="TUTOR"><TutorDashboard /></ProtectedRoute>} />
      <Route path="/students" element={<ProtectedRoute requiredRole="TUTOR"><StudentListPage /></ProtectedRoute>} />
      <Route path="/students/:studentId" element={<ProtectedRoute requiredRole="TUTOR"><StudentDetailPage /></ProtectedRoute>} />
      <Route path="/sessions/new" element={<ProtectedRoute requiredRole="TUTOR"><NewSessionPage /></ProtectedRoute>} />
      <Route path="/sessions/:sessionId" element={<ProtectedRoute requiredRole="TUTOR"><SessionDetailPage /></ProtectedRoute>} />

      <Route path="/student" element={<Navigate to="/student/dashboard" replace />} />
      <Route path="/student/dashboard" element={<ProtectedRoute requiredRole="STUDENT"><StudentDashboard /></ProtectedRoute>} />
      <Route path="/student/history" element={<ProtectedRoute requiredRole="STUDENT"><StudentHistoryPage /></ProtectedRoute>} />
      <Route path="/student/sessions/:sessionId" element={<ProtectedRoute requiredRole="STUDENT"><StudentSessionDetailPage /></ProtectedRoute>} />

      <Route path="*" element={<Navigate to={getDashboardPath(parseRoleFromToken(getToken()))} replace />} />
    </Routes>
  );
}
