import { Play } from "lucide-react";
import { FaSpotify } from "react-icons/fa";
import { useLocation, useNavigate } from "react-router-dom";
import { useMemo, useState } from "react";
import "../styles/Home.css";
import "../styles/Recommender.css";
import api from "../api";

export default function RecommendationResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const data = location.state;

  const { selected_track, random_list, variable_based_list, used_feature } = data || {};

  const toArray = (x) => (Array.isArray(x) ? x : []);
  const listRandom = toArray(random_list).slice(0, 3);
  const listVariableBased = toArray(variable_based_list).slice(0, 3);

  const [ratings, setRatings] = useState({});
  const [errorMsg, setErrorMsg] = useState("");
  const [openEmbedTrackId, setOpenEmbedTrackId] = useState(null);

  const [showLanguageQuestion, setShowLanguageQuestion] = useState(false);
  const [languageHadImpact, setLanguageHadImpact] = useState(null);
  const [languageImpactedTracks, setLanguageImpactedTracks] = useState({});

  const ratingOptions = useMemo(() => {
    return ["", ...Array.from({ length: 11 }, (_, i) => String(i))];
  }, []);

  const allDisplayedTracks = useMemo(() => {
    const safe = (t, idx, listType) => (t ? { t, idx, listType } : null);

    return [
      ...listRandom.map((t, idx) => safe(t, idx, "listRandom")).filter(Boolean),
      ...listVariableBased.map((t, idx) =>
        safe(t, idx, "listVariableBased")
      ).filter(Boolean),
    ];
  }, [listRandom, listVariableBased]);

  const getTrackId = (track, index, listType = "") =>
    track?.id ? `${listType}-${track.id}` : `${listType}-${track?.name}-${index}`;

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  const setRating = (trackId, value) => {
    setRatings((prev) => ({ ...prev, [trackId]: value }));
  };

  const toggleLanguageImpactTrack = (trackId) => {
    setLanguageImpactedTracks((prev) => ({
      ...prev,
      [trackId]: !prev[trackId],
    }));
  };

  const validateRatings = () => {
    for (const item of allDisplayedTracks) {
      const trackId = getTrackId(item.t, item.idx, item.listType);
      const value = ratings[trackId];

      if (value === undefined || value === "") {
        setErrorMsg("Preencha todas as notas (0 a 10) antes de prosseguir.");
        return false;
      }
    }

    return true;
  };

  const submitEvaluation = async () => {
    setErrorMsg("");

    if (!validateRatings()) return;

    if (!showLanguageQuestion) {
      setShowLanguageQuestion(true);
      return;
    }

    if (languageHadImpact === null) {
      setErrorMsg("Informe se a língua da música influenciou sua avaliação.");
      return;
    }

    if (
      languageHadImpact === true &&
      !Object.values(languageImpactedTracks).some(Boolean)
    ) {
      setErrorMsg("Selecione pelo menos uma música impactada pela língua.");
      return;
    }

    try {
      const payload = {
        base_track_id: selected_track?.id,
        used_feature: used_feature ?? null,

        base_track_name: selected_track?.name ?? "",
        base_track_artists: selected_track?.artists ?? "",
        recommendation_cluster: selected_track?.cluster ?? null,

        items: [
          ...listRandom.map((track, index) => {
            const trackId = getTrackId(track, index, "listRandom");

            return {
              track_id: track.id,
              order_in_list: index + 1,
              list_type: "listRandom",
              rating: Number(ratings[trackId]),
              language_influenced_rating:
                languageHadImpact === true &&
                Boolean(languageImpactedTracks[trackId]),
              base_metric: null,
              recommendation_cluster: track.cluster ?? null,
              recommended_track_name: track.name ?? "",
              recommended_track_artists: track.artists ?? "",
            };
          }),

          ...listVariableBased.map((track, index) => {
            const trackId = getTrackId(track, index, "listVariableBased");

            return {
              track_id: track.id,
              order_in_list: index + 1,
              list_type: "listVariableBased",
              rating: Number(ratings[trackId]),
              language_influenced_rating:
                languageHadImpact === true &&
                Boolean(languageImpactedTracks[trackId]),
              base_metric: used_feature ?? null,
              recommendation_cluster: track.cluster ?? null,
              recommended_track_name: track.name ?? "",
              recommended_track_artists: track.artists ?? "",
            };
          }),
        ],
      };

      const response = await api.post("/api/recommendation-evaluations/", payload);

      console.log("Avaliações salvas:", response.data);

      localStorage.removeItem("EVALUATION_DATA");
      navigate("/recommender");
    } catch (err) {
      console.error("Erro completo:", err);
      console.error("Status:", err.response?.status);
      console.error("Resposta do backend:", err.response?.data);
      console.error(err);
      setErrorMsg(
        "Erro ao salvar a avaliação. Por favor, tente novamente mais tarde ou entre em contato com o Administrador."
      );
    }
  };

  const handleBackToRecommender = () => {
    navigate("/recommender");
  };

  const getSpotifyTrackUrl = (spotifyId) =>
    `https://open.spotify.com/track/${spotifyId}`;

  const getSpotifyEmbedUrl = (spotifyId) =>
    `https://open.spotify.com/embed/track/${spotifyId}`;

  const toggleEmbed = (spotifyId) => {
    setOpenEmbedTrackId((prev) => (prev === spotifyId ? null : spotifyId));
  };

  const renderTrackItem = (track, index, listType) => {
    if (!track) return null;

    const trackId = getTrackId(track, index, listType);
    const ratingValue = ratings[trackId] ?? "";
    const spotifyId = track?.id;
    const isEmbedOpen = openEmbedTrackId === spotifyId;

    return (
      <li key={trackId} className="recommender-result-item rating-item">
        <div className="rating-track-info">
          <div
            className="track-label"
            title={`${track.name} — ${track.artists}`}
          >
            <strong>{index + 1}.</strong> {track.name} — {track.artists}
          </div>
        </div>

        <div className="rating-controls">
          <select
            className="rating-input"
            value={ratingValue}
            onChange={(e) => setRating(trackId, e.target.value)}
            disabled={showLanguageQuestion}
          >
            <option value="" disabled>
              Avalie...
            </option>
            {ratingOptions
              .filter((v) => v !== "")
              .map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
          </select>

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

        {showLanguageQuestion && languageHadImpact === true && (
          <label className="language-impact-checkbox">
            <input
              type="checkbox"
              checked={Boolean(languageImpactedTracks[trackId])}
              onChange={() => toggleLanguageImpactTrack(trackId)}
            />
            A língua desta música influenciou minha avaliação
          </label>
        )}

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
              title={`Spotify embed - ${track.name}`}
            />
          </div>
        )}
      </li>
    );
  };

  if (!data) {
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
          <h1 className="recommender-title">Nenhuma recomendação encontrada</h1>
          <button
            className="form-button home-button"
            onClick={() => navigate("/recommender")}
          >
            Ir para Nova Recomendação
          </button>
        </main>
      </div>
    );
  }

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
        </div>

        <div className="header-right">
          <span className="welcome-text">Olá, {username}</span>
          <button className="logout-button" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      <main className="form-container recommender-container">
        <h1 className="recommender-title">Avalie as Recomendações</h1>

        <p className="recommender-subtitle" style={{ marginTop: "0.5rem" }}>
          Recomendações geradas para{" "}
          <strong>{selected_track?.name || "a música selecionada"}</strong>
        </p>

        {errorMsg && (
          <div
            style={{
              marginTop: "1rem",
              padding: "0.75rem 1rem",
              borderRadius: "10px",
              background: "rgba(255, 0, 0, 0.08)",
              border: "1px solid rgba(255, 0, 0, 0.25)",
            }}
          >
            {errorMsg}
          </div>
        )}

        <div className="recommender-lists-grid">
          <section className="recommender-section">
            <h2 className="recommender-subtitle">Lista 1</h2>
            <ul className="recommender-results-list">
              {listRandom.map((t, i) => renderTrackItem(t, i, "listRandom"))}
            </ul>
          </section>

          <section className="recommender-section">
            <h2 className="recommender-subtitle">Lista 2</h2>
            <ul className="recommender-results-list">
              {listVariableBased.map((t, i) =>
                renderTrackItem(t, i, "listVariableBased")
              )}
            </ul>
          </section>
        </div>

        {showLanguageQuestion && (
          <section className="language-impact-card">
            <h2 className="recommender-subtitle">
              A língua da música influenciou sua avaliação?
            </h2>

            <div className="language-impact-options">
              <label>
                <input
                  type="radio"
                  name="languageImpact"
                  checked={languageHadImpact === true}
                  onChange={() => setLanguageHadImpact(true)}
                />
                Sim, influenciou uma ou mais avaliações
              </label>

              <label>
                <input
                  type="radio"
                  name="languageImpact"
                  checked={languageHadImpact === false}
                  onChange={() => {
                    setLanguageHadImpact(false);
                    setLanguageImpactedTracks({});
                  }}
                />
                Não influenciou minha avaliação
              </label>
            </div>

            {languageHadImpact === true && (
              <p className="recommender-empty" style={{ marginTop: "10px" }}>
                Marque o checkbox nas músicas em que a língua impactou sua nota.
              </p>
            )}
          </section>
        )}

        <div className="recommender-actions">
          <button
            className="form-button home-button recommender-back-button"
            onClick={handleBackToRecommender}
          >
            Voltar
          </button>

          <button
            className="form-button home-button recommender-submit-button"
            onClick={submitEvaluation}
          >
            {showLanguageQuestion ? "Confirmar e Salvar Avaliação" : "Submeter Avaliação"}
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
