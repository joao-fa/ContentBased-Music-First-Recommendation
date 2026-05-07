import { useNavigate } from "react-router-dom";
import newRecommendationImage from "../assets/recommender/new_recommendation.png";
import myRecommendationsImage from "../assets/recommender/my_recommendations.png";
import "../styles/Home.css";

function HomeActionCard({ title, description, image, alt, onClick }) {
  return (
    <button
      type="button"
      className="home-action-card"
      onClick={onClick}
    >
      <div className="home-action-card-image-frame">
        <img
          src={image}
          alt={alt}
          className="home-action-card-image"
        />
      </div>

      <div className="home-action-card-body">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </button>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  return (
    <div className="home-wrapper">
      <header className="home-header">
        <div className="header-left">
          <h2
            className="site-title"
            onClick={() => navigate("/")}
            style={{ cursor: "pointer" }}
          >
            CB Music First Recommendation
          </h2>

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

        <div className="home-buttons home-action-grid">
          <HomeActionCard
            title="Nova recomendação"
            description="Inicie uma nova busca e avalie novas recomendações."
            image={newRecommendationImage}
            alt="Ilustração representando uma nova recomendação"
            onClick={() => navigate("/recommender")}
          />

          <HomeActionCard
            title="Minhas recomendações"
            description="Confira o histórico das recomendações que você já avaliou."
            image={myRecommendationsImage}
            alt="Ilustração representando minhas recomendações"
            onClick={() => navigate("/my-recommendations")}
          />
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