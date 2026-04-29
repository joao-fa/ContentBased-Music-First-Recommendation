import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import "../styles/Auth.css";

export default function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showCredentialWarning, setShowCredentialWarning] = useState(true);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/user/register/", { username, password });
      navigate("/login");
    } catch (err) {
      alert("Erro ao registrar: " + err.message);
    }
  };

  return (
    <div className="auth-page">
      {showCredentialWarning && (
        <div className="auth-modal-overlay" role="dialog" aria-modal="true">
          <div className="auth-modal">
            <h2 className="auth-modal-title">Aviso sobre credenciais</h2>

            <p className="auth-modal-text">
              Para participar deste projeto acadêmico, recomendamos que você utilize
              um usuário e uma senha descartáveis, criados apenas para este sistema.
            </p>

            <p className="auth-modal-text">
              Não utilize senhas pessoais, senhas já usadas em outros serviços, e-mail
              pessoal como nome de usuário, ou qualquer credencial relacionada a contas
              importantes.
            </p>

            <button
              type="button"
              className="auth-modal-button"
              onClick={() => setShowCredentialWarning(false)}
            >
              Entendi
            </button>
          </div>
        </div>
      )}

      <header className="auth-header">
        <h1
          className="site-title"
          onClick={() => navigate("/")}
          style={{ cursor: "pointer" }}
        >
          CB Music First Recommendation
        </h1>
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
