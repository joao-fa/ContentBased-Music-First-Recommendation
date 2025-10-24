import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import "../styles/Auth.css";

export default function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/register/", { username, password });
      navigate("/login");
    } catch (err) {
      alert("Erro ao registrar: " + err.message);
    }
  };

  return (
    <div className="auth-page">
      <header className="auth-header">
        <h1 className="site-title">CB Music First Recommendation</h1>
      </header>
      <main className="auth-container">
        <h2 className="auth-heading">Registro</h2>
        <form className="auth-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Usuário"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit">Registrar</button>
        </form>
        <p className="auth-link">
          Já tem uma conta?{" "}
          <span onClick={() => navigate("/login")}>Entrar</span>
        </p>
      </main>
    </div>
  );
}
