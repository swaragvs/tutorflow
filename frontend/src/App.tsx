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
    throw new Error(message);
  }

  return response;
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

function formatDateTime(value: string) {
  const date = new Date(value);
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

function getSessionTitle(session: Session) {
  return `Session #${formatShortId(session.id)}`;
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
  return student.email || `Student ${formatShortId(student.user_id, "Unknown")}`;
}

function sortSessions(sessions: Session[]) {
  return [...sessions].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
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

  const navLinks = (
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
          {actions}
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

        {error ? <div className="error-banner">{error}</div> : null}
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await apiFetch("/sessions");
        const data: Session[] = await response.json();
        setSessions(sortSessions(data));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load sessions");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const upcoming = useMemo(
    () =>
      sessions
        .filter((session) => session.status === "SCHEDULED" || session.status === "IN_PROGRESS")
        .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()),
    [sessions],
  );

  return (
    <AppLayout title="Tutor Dashboard" actions={<Link to="/sessions/new" className="primary-link">Schedule Session</Link>}>
      {error ? <div className="error-banner">{error}</div> : null}
      {loading ? <p>Loading...</p> : null}
      <div className="section-header">
        <h2>Upcoming sessions</h2>
        <Link to="/students">Manage students</Link>
      </div>
      {!loading && upcoming.length === 0 ? <p>No upcoming sessions.</p> : null}
      <div className="card-list">
        {upcoming.map((session) => (
          <Link key={session.id} to={`/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{formatStatusLabel(session.status)}</strong>
              <span>{getSessionTitle(session)}</span>
            </div>
            <div><strong>Time:</strong> {formatDateTime(session.start_time)} → {formatDateTime(session.end_time)}</div>
            <div><strong>Session ID:</strong> {session.id}</div>
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
      setForm({ email: "", initial_password: "", learning_goals: "", skill_level: "", preferences: "" });
      setShowForm(false);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create student");
    }
  };

  return (
    <AppLayout title="Students">
      {error ? <div className="error-banner">{error}</div> : null}
      {createdStudent ? (
        <div className="success-banner">
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
            <div><strong>Student ID:</strong> {formatShortId(student.user_id, "Unknown")}</div>
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

  useEffect(() => {
    const load = async () => {
      if (!studentId) return;
      try {
        const studentResponse = await apiFetch(`/students/${studentId}`);
        const studentData = await studentResponse.json();
        setStudent(studentData);

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
        <div className="error-banner">{error || "Student not found."}</div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title={student.email ?? "Student details"}
      actions={<Link to={`/sessions/new?studentId=${student.user_id}`} className="primary-link">Schedule session</Link>}
    >
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

      <h2>Session history</h2>
      {sessions.length === 0 ? <p>No sessions.</p> : null}
      <div className="card-list">
        {sessions.map((session) => (
          <Link key={session.id} to={`/sessions/${session.id}`} className="session-card">
            <div className="row-between">
              <strong>{formatStatusLabel(session.status)}</strong>
              <span>{getSessionTitle(session)}</span>
            </div>
            <div><strong>Time:</strong> {formatDateTime(session.start_time)} → {formatDateTime(session.end_time)}</div>
            <div><strong>Session ID:</strong> {session.id}</div>
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
      const message = err instanceof Error ? err.message : "Unable to create session";
      setError(message);
    }
  };

  return (
    <AppLayout title="Schedule session">
      {error ? <div className="error-banner">{error}</div> : null}
      {loading ? <p>Loading students...</p> : (
        <form onSubmit={handleSubmit} className="stacked-form form-card">
          <label>
            Student
            <select value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
              {students.map((student) => (
                <option key={student.user_id} value={student.user_id}>{student.email ?? student.user_id}</option>
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

function SessionDetailPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [homeworkDraft, setHomeworkDraft] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadSession = async () => {
    if (!sessionId) return;
    try {
      const response = await apiFetch(`/sessions/${sessionId}`);
      const data: Session = await response.json();
      setSession(data);
      setNotesDraft(data.notes ?? "");
      setHomeworkDraft(data.homework ?? "");
      setError("");
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

  const handleGeneratePlan = async () => {
    if (!session) return;
    const durationMinutes = Math.max(
      1,
      Math.round((new Date(session.end_time).getTime() - new Date(session.start_time).getTime()) / 60000),
    );

    try {
      const response = await apiFetch(`/sessions/${session.id}/ai-plan`, {
        method: "POST",
        body: JSON.stringify({ duration_minutes: durationMinutes }),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate AI plan");
    }
  };

  const handleSaveNotes = async () => {
    if (!session) return;
    try {
      const response = await apiFetch(`/sessions/${session.id}/notes`, {
        method: "PATCH",
        body: JSON.stringify({ notes: notesDraft }),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save notes");
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
      const response = await apiFetch(`/sessions/${session.id}/trigger-ai-review`, {
        method: "PATCH",
        body: JSON.stringify({}),
      });
      const data: Session = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to trigger AI review");
    }
  };

  if (loading) return <AppLayout title="Session detail"><p>Loading...</p></AppLayout>;
  if (!session) {
    return (
      <AppLayout title="Session detail">
        <div className="error-banner">{error || "Session not found."}</div>
      </AppLayout>
    );
  }

  const aiPlan = parseJsonField(session.ai_plan);
  const aiSummary = parseJsonField(session.ai_summary);
  const isCompleteReady = notesDraft.trim().length > 0 && homeworkDraft.trim().length > 0;

  return (
    <AppLayout title={getSessionTitle(session)} actions={<button type="button" onClick={() => navigate("/dashboard")}>Back to dashboard</button>}>
      {error ? <div className="error-banner">{error}</div> : null}
      <div className="session-meta">
        <span className={`status-badge status-${session.status.toLowerCase()}`}>{formatStatusLabel(session.status)}</span>
        <span><strong>Time:</strong> {formatDateTime(session.start_time)} → {formatDateTime(session.end_time)}</span>
      </div>

      {session.status === "SCHEDULED" ? (
        <div className="action-row">
          <button type="button" onClick={handleGeneratePlan}>Generate AI Plan</button>
          <button type="button" onClick={handleStart}>Start Session</button>
        </div>
      ) : null}

      {session.status === "IN_PROGRESS" ? (
        <div className="stacked-form form-card">
          <label>
            Notes
            <textarea value={notesDraft} onChange={(e) => setNotesDraft(e.target.value)} rows={6} />
          </label>
          <label>
            Homework
            <textarea value={homeworkDraft} onChange={(e) => setHomeworkDraft(e.target.value)} rows={4} />
          </label>
          <div className="action-row">
            <button type="button" onClick={handleSaveNotes}>Save notes</button>
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
          <button type="button" onClick={handleTriggerAiReview}>Trigger AI Review</button>
        </div>
      ) : null}

      {session.status === "SCHEDULED" || session.status === "IN_PROGRESS" || session.status === "COMPLETED" ? (
        <div className="info-block">
          <h3>Session details</h3>
          {session.notes ? <p><strong>Notes:</strong> {session.notes}</p> : <p>No notes yet.</p>}
          {session.homework ? <p><strong>Homework:</strong> {session.homework}</p> : <p>No homework assigned yet.</p>}
        </div>
      ) : null}

      {session.status === "AI_REVIEWED" && aiSummary ? (
        <div className="info-block">
          <h3>AI Summary</h3>
          <p><strong>Summary:</strong> {aiSummary.summary}</p>
          <p><strong>Strengths:</strong> {aiSummary.strengths?.join(", ")}</p>
          <p><strong>Areas to improve:</strong> {aiSummary.areas_to_improve?.join(", ")}</p>
          <p><strong>Recommended next topic:</strong> {aiSummary.recommended_next_topic}</p>
        </div>
      ) : null}

      {aiPlan && typeof aiPlan === "object" ? (
        <div className="info-block">
          <h3>AI Plan</h3>
          <p><strong>Warm up:</strong> {aiPlan.warm_up}</p>
          <p><strong>Main focus:</strong> {aiPlan.main_focus}</p>
          <p><strong>Practice activities:</strong> {Array.isArray(aiPlan.practice_activities) ? aiPlan.practice_activities.join("; ") : ""}</p>
          <p><strong>Check for understanding:</strong> {aiPlan.check_for_understanding}</p>
        </div>
      ) : null}
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
      <Route path="*" element={<Navigate to={getDashboardPath(parseRoleFromToken(getToken()))} replace />} />
    </Routes>
  );
}
