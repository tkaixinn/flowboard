import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5001";

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [isAuthPage, setIsAuthPage] = useState(!token);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [stats, setStats] = useState(null);
  const [category, setCategory] = useState("General");
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editCategory, setEditCategory] = useState("");

  const fetchTasks = async (authToken) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/tasks`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setTasks(res.data);
      const statsRes = await axios.get(`${API_BASE_URL}/stats`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setStats(statsRes.data);
      setError("");
    } catch (err) {
      const status = err.response?.status;
      if (status === 401 || status === 422) {
        localStorage.removeItem("token");
        setToken(null);
        setIsAuthPage(true);
        setError("Session expired or invalid token. Please log in again.");
        return;
      }
      if (!err.response) {
        setError("Cannot reach backend API. Make sure backend is running on port 5001.");
        return;
      }
      setError(err.response?.data?.msg || "Failed to fetch tasks.");
    }
  };

  const startEditingTask = (task) => {
    setEditingTaskId(task.id);
    setEditTitle(task.title);
    setEditCategory(task.category || "General");
  };

  const saveTaskEdit = async (task) => {
    if (!editTitle.trim()) {
      setError("Task title cannot be empty.");
      return;
    }
    try {
      await axios.put(
        `${API_BASE_URL}/tasks/${task.id}`,
        { title: editTitle, category: editCategory || "General" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEditingTaskId(null);
      setEditTitle("");
      setEditCategory("");
      fetchTasks(token);
    } catch (err) {
      setError("Failed to update task.");
    }
  };

  const cancelTaskEdit = () => {
    setEditingTaskId(null);
    setEditTitle("");
    setEditCategory("");
  };

  const handleRegister = async () => {
    if (!username.trim() || !password.trim()) {
      setError("Username and password are required");
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/register`, {
        username,
        password
      });
      setError(res.data.msg);
      setUsername("");
      setPassword("");
    } catch (err) {
      setError(err.response?.data?.msg || "Registration failed");
    }
  };

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setError("Username and password are required");
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/login`, {
        username,
        password
      });
      const newToken = res.data.access_token;
      setToken(newToken);
      localStorage.setItem("token", newToken);
      setIsAuthPage(false);
      setUsername("");
      setPassword("");
      setError("");
      fetchTasks(newToken);
    } catch (err) {
      setError(err.response?.data?.msg || "Login failed");
    }
  };

  const handleLogout = () => {
    setToken(null);
    setTasks([]);
    setStats(null);
    localStorage.removeItem("token");
    setIsAuthPage(true);
    setUsername("");
    setPassword("");
  };

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      await axios.post(
        `${API_BASE_URL}/tasks`,
        { title: newTask, category, due_date: dueDate || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setNewTask("");
      setDueDate("");
      setCategory("General");
      fetchTasks(token);
    } catch (err) {
      setError("Failed to add task.");
    }
  };

  const toggleComplete = async (task) => {
    try {
      await axios.put(`${API_BASE_URL}/tasks/${task.id}`, 
        { completed: !task.completed },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchTasks(token);
    } catch (err) {
      setError("Failed to update task. Check backend connection.");
    }
  };

  const deleteTask = async (task) => {
    try {
      await axios.delete(`${API_BASE_URL}/tasks/${task.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchTasks(token);
    } catch (err) {
      setError("Failed to delete task. Check backend connection.");
    }
  };

  useEffect(() => {
    if (token) {
      fetchTasks(token);
    }
  }, [token]);

  if (isAuthPage) {
    return (
      <main className="page page-auth">
        <section className="card auth-card">
          <h1 className="page-title">Flowboard</h1>
          <p className="page-subtitle">Login or create an account to manage your tasks.</p>
          {error && <p className="error-banner">{error}</p>}

          <label className="field-label" htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="field-input"
          />

          <label className="field-label" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="field-input"
          />

          <div className="auth-actions">
            <button onClick={handleLogin} className="btn btn-primary btn-full">
              Login
            </button>
            <button onClick={handleRegister} className="btn btn-secondary btn-full">
              Register
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="page page-dashboard">
      <section className="card dashboard-card">
        <header className="dashboard-header">
          <div>
            <h1 className="page-title">Personal Dashboard</h1>
            <p className="page-subtitle">Track your tasks, categories, and due dates.</p>
          </div>
          <button onClick={handleLogout} className="btn btn-danger">
            Logout
          </button>
        </header>

        {error && <p className="error-banner">{error}</p>}

        <section className="composer">
          <input
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            className="field-input"
            placeholder="Task name"
          />
          <div className="composer-row">
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="field-input"
            />
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="Category"
              className="field-input"
            />
            <button onClick={addTask} className="btn btn-primary composer-add">
              Add Task
            </button>
          </div>
        </section>

        {stats && (
          <section className="stats-grid">
            <article className="stat-tile">
              <span className="stat-label">Total</span>
              <strong className="stat-value">{stats.total}</strong>
            </article>
            <article className="stat-tile">
              <span className="stat-label">Completed</span>
              <strong className="stat-value">{stats.completed}</strong>
            </article>
            <article className="stat-tile">
              <span className="stat-label">Completion</span>
              <strong className="stat-value">{(stats.completion_rate * 100).toFixed(0)}%</strong>
            </article>
          </section>
        )}

        <ul className="task-list">
          {tasks.map((task) => {
            const isOverdue =
              task.due_date &&
              new Date(task.due_date) < new Date() &&
              !task.completed;

            return (
              <li key={task.id} className="task-item">
                <div className="task-main">
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => toggleComplete(task)}
                    className="task-check"
                  />

                  <div className="task-content">
                    {editingTaskId === task.id ? (
                      <div className="edit-fields">
                        <input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="field-input"
                        />
                        <input
                          value={editCategory}
                          onChange={(e) => setEditCategory(e.target.value)}
                          placeholder="Category"
                          className="field-input"
                        />
                      </div>
                    ) : (
                      <>
                        <h3
                          className={`task-title ${task.completed ? "task-title-done" : ""} ${isOverdue ? "task-title-overdue" : ""}`}
                        >
                          {task.title}
                        </h3>
                        <div className="task-meta">
                          <span className="category-chip">{task.category || "General"}</span>
                          {task.due_date && (
                            <span className={`due-text ${isOverdue ? "due-overdue" : ""}`}>
                              Due {task.due_date}{isOverdue ? " - Overdue" : ""}
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="task-actions">
                  {editingTaskId === task.id ? (
                    <>
                      <button onClick={() => saveTaskEdit(task)} className="btn btn-success btn-small">
                        Save
                      </button>
                      <button onClick={cancelTaskEdit} className="btn btn-muted btn-small">
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button onClick={() => startEditingTask(task)} className="btn btn-warning btn-small">
                      Edit
                    </button>
                  )}

                  <button onClick={() => deleteTask(task)} className="btn btn-danger-soft btn-small">
                    Delete
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}

export default App;