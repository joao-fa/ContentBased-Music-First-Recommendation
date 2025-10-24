import { useNavigate } from "react-router-dom";
import "../styles/Home.css";

export default function Home() {
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  return (
    <div className="home-wrapper">
      {}
      <header className="home-header">
        <div className="header-left">
          <h2 className="site-title">CB Music First Recommendation</h2>

          <div className="header-nav">
            <button
              className="header-button"
              onClick={() => navigate("/recommender")}
            >
              Nova Recomendação
            </button>

            <button
              className="header-button"
              onClick={() => navigate("/my-recommendations")}
            >
              Minhas Recomendações
            </button>

            <button
              className="header-button"
              onClick={() => navigate("/references")}
            >
              Referências
            </button>
          </div>
        </div>

        <div className="header-right">
          <span className="welcome-text">Olá, {username}</span>
          <button className="logout-button" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      <main className="form-container home-container">
        <h1 className="home-title">Content Based Music First Recommendation</h1>
        <p className="home-description">
          Gere recomendações a partir de uma única música.
        </p>

        <div className="home-buttons">
          <button
            className="form-button home-button"
            onClick={() => navigate("/recommender")}
          >
            Nova Recomendação
          </button>
          <button
            className="form-button home-button"
            onClick={() => navigate("/my-recommendations")}
          >
            Minhas Recomendações
          </button>
        </div>
      </main>
      <footer className="home-footer">
        <div className="footer-content">
          <p className="footer-text">
            Projeto acadêmico desenvolvido para pesquisa em sistemas de recomendação musical baseados em conteúdo. Consulte as referências na aba 'Referências'. 
          </p>
          <p className="footer-info">
            © {new Date().getFullYear()} João Víctor Ferreira Araujo — Universidade de São Paulo (EACH-USP)
          </p>
          <a
            className="footer-link"
            href="https://github.com/joao-fa/ContentBased-Music-First-Recommendation"
            target="_blank"
            rel="noopener noreferrer"
          >
            Ver projeto no GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
