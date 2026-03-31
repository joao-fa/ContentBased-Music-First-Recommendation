import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, ChevronDown, ChevronUp } from "lucide-react";
import { FaSpotify } from "react-icons/fa";
import api from "../api";
import "../styles/Home.css";
import "../styles/Recommender.css";
import "../styles/MyRecommendations.css";

export default function MyRecommendations() {
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [expandedBatchId, setExpandedBatchId] = useState(null);
  const [openEmbedTrackId, setOpenEmbedTrackId] = useState(null);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        setLoading(true);
        setErrorMsg("");

        const response = await api.get("/api/my-recommendation-evaluations/");
        const data = Array.isArray(response.data)
            ? response.data
            : response.data.results || [];

        setBatches(data);
      } catch (err) {
        console.error(err);
        setErrorMsg("Erro ao carregar suas recomendações.");
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  const toggleBatch = (batchId) => {
    setExpandedBatchId((prev) => (prev === batchId ? null : batchId));
    setOpenEmbedTrackId(null);
  };

  const toggleEmbed = (spotifyId) => {
    setOpenEmbedTrackId((prev) => (prev === spotifyId ? null : spotifyId));
  };

  const getSpotifyTrackUrl = (spotifyId) =>
    `https://open.spotify.com/track/${spotifyId}`;

  const getSpotifyEmbedUrl = (spotifyId) =>
    `https://open.spotify.com/embed/track/${spotifyId}`;

  const formatDateTime = (value) => {
    if (!value) return "";
    return new Date(value).toLocaleString("pt-BR");
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
            <button className="header-button" onClick={() => navigate("/recommender")}>
              Nova Recomendação
            </button>

            <button className="header-button" onClick={() => navigate("/my-recommendations")}>
              Minhas Recomendações
            </button>

            <button className="header-button" onClick={() => navigate("/references")}>
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

      <main className="form-container recommender-container">
        <h1 className="recommender-title">Minhas Recomendações</h1>
        <p className="recommender-description">
          Visualize as músicas base que você selecionou e as recomendações avaliadas.
        </p>

        {loading && <p className="recommender-empty">Carregando recomendações...</p>}

        {!loading && errorMsg && <p className="recommender-error">{errorMsg}</p>}

        {!loading && !errorMsg && batches.length === 0 && (
          <p className="recommender-empty">Você ainda não possui recomendações avaliadas.</p>
        )}

        {!loading && !errorMsg && batches.length > 0 && (
          <div className="my-recommendations-list">
            {batches.map((batch) => {
              const isExpanded = expandedBatchId === batch.id;
              const recommendations = Array.isArray(batch.recommendations)
                ? batch.recommendations
                : [];

              return (
                <section key={batch.id} className="my-rec-card">
                  <button
                    type="button"
                    className="my-rec-header"
                    onClick={() => toggleBatch(batch.id)}
                  >
                    <div className="my-rec-header-text">
                      <h2 className="my-rec-title">{batch.base_track_name}</h2>
                      <p className="my-rec-subtitle">{batch.base_track_artists}</p>
                      <p className="my-rec-date">
                        Recomendação feita em {formatDateTime(batch.created_at)}
                      </p>
                    </div>

                    <span className="my-rec-icon">
                      {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="my-rec-body">
                      <ul className="recommender-results-list">
                        {recommendations.map((item, index) => {
                          const spotifyId = item.recommended_track;
                          const isEmbedOpen = openEmbedTrackId === spotifyId;

                          return (
                            <li
                              key={item.id}
                              className="recommender-result-item rating-item my-rec-item"
                            >
                              <div className="my-rec-content">
                                <div className="rating-track-info my-rec-track-info">
                                    <div
                                    className="track-label my-rec-track-label"
                                    title={`${item.recommended_track_name} — ${item.recommended_track_artists}`}
                                    >
                                    <strong>{index + 1}.</strong> {item.recommended_track_name} —{" "}
                                    {item.recommended_track_artists}
                                    </div>
                                </div>

                                <div className="my-rec-actions">
                                    <span className="my-rec-rating-text">
                                    Avaliada com a nota: <strong>{item.rating}</strong>
                                    </span>

                                    <div className="rating-controls">
                                    <a
                                        className="spotify-icon-btn"
                                        href={getSpotifyTrackUrl(spotifyId)}
                                        target="_blank"
                                        rel="noreferrer"
                                        title="Abrir no Spotify"
                                    >
                                        <FaSpotify size={16} />
                                    </a>

                                    <button
                                        type="button"
                                        className="spotify-icon-btn"
                                        onClick={() => toggleEmbed(spotifyId)}
                                        title="Ouvir aqui"
                                    >
                                        <Play size={16} />
                                    </button>
                                    </div>
                                </div>
                                </div>

                              {isEmbedOpen && (
                                <div className="spotify-embed-container">
                                  <iframe
                                    style={{ borderRadius: 12 }}
                                    src={getSpotifyEmbedUrl(spotifyId)}
                                    width="100%"
                                    height="152"
                                    frameBorder="0"
                                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                                    loading="lazy"
                                    title={`Spotify embed - ${item.recommended_track_name}`}
                                  />
                                </div>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        )}
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