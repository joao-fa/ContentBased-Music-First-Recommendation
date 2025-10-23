import { useNavigate } from "react-router-dom";
import "../styles/Form.css";
import "../styles/Home.css";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="form-container home-container">
      <h1 className="home-title">ContentBased Music First Recommendation</h1>
      <p className="home-description">
        Gere recomendações a partir de uma única música.
      </p>

      <div className="home-buttons">
        <button
          className="form-button home-button"
          onClick={() => navigate("/my-recommendations")}
        >
          Minhas Recomendações
        </button>

        <button
          className="form-button home-button"
          onClick={() => navigate("/recommender")}
        >
          Nova Recomendação
        </button>
      </div>
    </div>
  );
}
