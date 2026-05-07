import { useState } from "react";
import { HelpCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import "../styles/Auth.css";

export default function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showCredentialWarning, setShowCredentialWarning] = useState(true);

  const validateForm = () => {
    const trimmedUsername = username.trim();

    if (!trimmedUsername) {
      setErrorMsg("Informe um nome de usuário.");
      return false;
    }

    if (!password || !passwordConfirmation) {
      setErrorMsg("Preencha a senha e a confirmação de senha.");
      return false;
    }

    if (password !== passwordConfirmation) {
      setErrorMsg("As senhas digitadas não coincidem.");
      return false;
    }

    if (password.length < 4) {
      setErrorMsg("A senha deve ter pelo menos 4 caracteres.");
      return false;
    }

    setErrorMsg("");
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      setSubmitting(true);
      setErrorMsg("");

      await api.post("/api/user/register/", {
        username: username.trim(),
        password,
      });

      navigate("/login");
    } catch (err) {
      console.error(err);
      setErrorMsg(
        "Erro ao registrar. Verifique os dados informados ou tente novamente mais tarde."
      );
    } finally {
      setSubmitting(false);
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

      <main className="auth-container auth-register-container">
        <div className="auth-register-badge">Novo participante</div>

        <h2 className="auth-heading auth-register-heading">Criar conta</h2>

        <p className="auth-register-description">
          Cadastre um usuário descartável para participar da avaliação acadêmica
          do sistema de recomendação musical.
        </p>

        <div className="auth-data-help">
          <span>Estes dados serão utilizados para quê?</span>

          <span
            className="auth-data-tooltip-wrapper"
            tabIndex={0}
            aria-label="Informações sobre uso dos dados de cadastro"
          >
            <HelpCircle size={17} />

            <span className="auth-data-tooltip">
              Os dados informados não serão utilizados para fins além deste projeto
              de mestrado. Eles serão mantidos em bancos hospedados e servirão apenas
              para distinguir as avaliações realizadas no sistema.
            </span>
          </span>
        </div>

        {errorMsg && <p className="auth-error">{errorMsg}</p>}

        <form className="auth-form auth-register-form" onSubmit={handleSubmit}>
          <label className="auth-field">
            <span>Usuário</span>
            <input
              type="text"
              placeholder="Crie um usuário para este sistema"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label className="auth-field">
            <span>Senha</span>
            <input
              type="password"
              placeholder="Crie uma senha descartável"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <label className="auth-field">
            <span>Confirme sua senha</span>
            <input
              type="password"
              placeholder="Digite novamente sua senha"
              value={passwordConfirmation}
              onChange={(e) => setPasswordConfirmation(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          <button type="submit" disabled={submitting}>
            {submitting ? "Registrando..." : "Criar conta"}
          </button>
        </form>

        <p className="auth-link">
          Já tem uma conta?{" "}
          <span onClick={() => navigate("/login")}>Entrar</span>
        </p>
      </main>
    </div>
  );
}