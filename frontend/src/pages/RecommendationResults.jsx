import { HelpCircle, Play } from "lucide-react";
import { FaSpotify } from "react-icons/fa";
import { useLocation, useNavigate } from "react-router-dom";
import { useMemo, useRef, useState } from "react";
import "../styles/Home.css";
import "../styles/Recommender.css";
import api from "../api";

export default function RecommendationResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const data = location.state;

  const {
    selected_track,
    random_list,
    variable_based_list,
    used_feature,
    reference_feature_value,
    cluster,
  } = data || {};

  const createSessionUuid = () => {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
      return crypto.randomUUID();
    }

    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
      const random = (Math.random() * 16) | 0;
      const value = char === "x" ? random : (random & 0x3) | 0x8;
      return value.toString(16);
    });
  };

  const sessionUuidRef = useRef(createSessionUuid());
  const clientStartedAtRef = useRef(new Date().toISOString());

  const toArray = (x) => (Array.isArray(x) ? x : []);

  const frozenListsRef = useRef(null);

  if (data && frozenListsRef.current === null) {
    const initialRandomList = toArray(random_list).slice(0, 3);
    const initialVariableBasedList = toArray(variable_based_list).slice(0, 3);
    const shouldShowRandomFirst = Math.random() < 0.5;

    const randomListConfig = {
      displayLabel: shouldShowRandomFirst ? "Lista 1" : "Lista 2",
      listType: "listRandom",
      tracks: initialRandomList,
    };

    const variableBasedListConfig = {
      displayLabel: shouldShowRandomFirst ? "Lista 2" : "Lista 1",
      listType: "listVariableBased",
      tracks: initialVariableBasedList,
    };

    const displayedLists = shouldShowRandomFirst
      ? [randomListConfig, variableBasedListConfig]
      : [variableBasedListConfig, randomListConfig];

    const displayOrderConfig = displayedLists.reduce((acc, listConfig) => {
      acc[listConfig.displayLabel] = listConfig.listType;
      return acc;
    }, {});

    frozenListsRef.current = {
      listRandom: initialRandomList,
      listVariableBased: initialVariableBasedList,
      displayedLists,
      displayOrderConfig,
    };
  }

  const listRandom = frozenListsRef.current?.listRandom ?? [];
  const listVariableBased = frozenListsRef.current?.listVariableBased ?? [];
  const displayedLists = frozenListsRef.current?.displayedLists ?? [];
  const displayOrderConfig = frozenListsRef.current?.displayOrderConfig ?? {};

  const [ratings, setRatings] = useState({});
  const [errorMsg, setErrorMsg] = useState("");
  const [openEmbedTrackKey, setOpenEmbedTrackKey] = useState(null);

  const [previewOpenedTracks, setPreviewOpenedTracks] = useState({});
  const [spotifyOpenedTracks, setSpotifyOpenedTracks] = useState({});

  const [showLanguageQuestion, setShowLanguageQuestion] = useState(false);
  const [languageHadImpact, setLanguageHadImpact] = useState(null);
  const [languageImpactedTracks, setLanguageImpactedTracks] = useState({});

  const [evaluationSubmitted, setEvaluationSubmitted] = useState(false);

  const ratingOptions = useMemo(() => {
    return ["", ...Array.from({ length: 11 }, (_, i) => String(i))];
  }, []);

  const allDisplayedTracks = useMemo(() => {
    return displayedLists.flatMap((listConfig) =>
      listConfig.tracks
        .map((track, index) =>
          track
            ? {
                t: track,
                idx: index,
                listType: listConfig.listType,
              }
            : null
        )
        .filter(Boolean)
    );
  }, [displayedLists]);

  const getTrackKey = (track, index, listType = "") => {
    if (track?.id) {
      return `${listType}-${track.id}`;
    }

    return `${listType}-${track?.name || "track"}-${index}`;
  };

  const getFeatureValue = (track, feature) => {
    if (!track || !feature) return null;

    const value = track[feature];

    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    return null;
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  const setRating = (trackKey, value) => {
    setRatings((prev) => ({ ...prev, [trackKey]: value }));
  };

  const toggleLanguageImpactTrack = (trackKey) => {
    setLanguageImpactedTracks((prev) => ({
      ...prev,
      [trackKey]: !prev[trackKey],
    }));
  };

  const validateRatings = () => {
    for (const item of allDisplayedTracks) {
      const trackKey = getTrackKey(item.t, item.idx, item.listType);
      const value = ratings[trackKey];

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
      const clientSubmittedAt = new Date();
      const clientStartedAt = new Date(clientStartedAtRef.current);
      const durationSeconds = Math.max(
        0,
        Math.round((clientSubmittedAt.getTime() - clientStartedAt.getTime()) / 1000)
      );

      const payload = {
        session_uuid: sessionUuidRef.current,
        client_started_at: clientStartedAtRef.current,
        client_submitted_at: clientSubmittedAt.toISOString(),
        duration_seconds: durationSeconds,
        experiment_config: {
          used_feature: used_feature ?? null,
          reference_feature_value: reference_feature_value ?? null,
          cluster: cluster ?? selected_track?.cluster ?? null,
          random_list_size: listRandom.length,
          variable_based_list_size: listVariableBased.length,
          display_order: displayOrderConfig,
        },

        base_track_id: selected_track?.id,
        used_feature: used_feature ?? null,

        base_track_name: selected_track?.name ?? "",
        base_track_artists: selected_track?.artists ?? "",
        recommendation_cluster: selected_track?.cluster ?? null,

        items: [
          ...listRandom.map((track, index) => {
            const trackKey = getTrackKey(track, index, "listRandom");

            return {
              track_id: track.id,
              order_in_list: index + 1,
              list_type: "listRandom",
              rating: Number(ratings[trackKey]),
              language_influenced_rating:
                languageHadImpact === true &&
                Boolean(languageImpactedTracks[trackKey]),
              base_metric: null,
              recommendation_cluster: track.cluster ?? null,
              base_track_feature_value: null,
              recommended_track_feature_value: null,
              was_preview_opened: Boolean(previewOpenedTracks[trackKey]),
              spotify_opened: Boolean(spotifyOpenedTracks[trackKey]),
              recommended_track_name: track.name ?? "",
              recommended_track_artists: track.artists ?? "",
            };
          }),

          ...listVariableBased.map((track, index) => {
            const trackKey = getTrackKey(track, index, "listVariableBased");

            return {
              track_id: track.id,
              order_in_list: index + 1,
              list_type: "listVariableBased",
              rating: Number(ratings[trackKey]),
              language_influenced_rating:
                languageHadImpact === true &&
                Boolean(languageImpactedTracks[trackKey]),
              base_metric: used_feature ?? null,
              recommendation_cluster: track.cluster ?? null,
              base_track_feature_value:
                reference_feature_value ?? getFeatureValue(selected_track, used_feature),
              recommended_track_feature_value: getFeatureValue(track, used_feature),
              was_preview_opened: Boolean(previewOpenedTracks[trackKey]),
              spotify_opened: Boolean(spotifyOpenedTracks[trackKey]),
              recommended_track_name: track.name ?? "",
              recommended_track_artists: track.artists ?? "",
            };
          }),
        ],
      };

      const response = await api.post("/api/recommendation-evaluations/", payload);

      console.log("Avaliações salvas:", response.data);

      localStorage.removeItem("EVALUATION_DATA");
      setEvaluationSubmitted(true);
      setOpenEmbedTrackKey(null);
      window.scrollTo({ top: 0, behavior: "smooth" });
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

  const markSpotifyOpened = (trackKey) => {
    setSpotifyOpenedTracks((prev) => ({
      ...prev,
      [trackKey]: true,
    }));
  };

  const toggleEmbed = (trackKey) => {
    setPreviewOpenedTracks((prev) => ({
      ...prev,
      [trackKey]: true,
    }));

    setOpenEmbedTrackKey((prev) => (prev === trackKey ? null : trackKey));
  };

  const renderTrackItem = (track, index, listType) => {
    if (!track) return null;

    const trackKey = getTrackKey(track, index, listType);
    const ratingValue = ratings[trackKey] ?? "";
    const spotifyId = track?.id;
    const isEmbedOpen = openEmbedTrackKey === trackKey;

    return (
      <li key={trackKey} className="recommender-result-item rating-item">
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
            onChange={(e) => setRating(trackKey, e.target.value)}
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
            onClick={() => markSpotifyOpened(trackKey)}
          >
            <FaSpotify size={16} />
          </a>

          <button
            type="button"
            className="spotify-icon-btn"
            onClick={() => toggleEmbed(trackKey)}
            title="Ouvir aqui"
          >
            <Play size={16} />
          </button>
        </div>

        {showLanguageQuestion && languageHadImpact === true && (
          <label className="language-impact-checkbox">
            <input
              type="checkbox"
              checked={Boolean(languageImpactedTracks[trackKey])}
              onChange={() => toggleLanguageImpactTrack(trackKey)}
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

  if (evaluationSubmitted) {
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
          <h1 className="recommender-title">Avaliação concluída</h1>

          <p className="recommender-subtitle" style={{ marginTop: "0.75rem" }}>
            Obrigado por submeter sua avaliação. Sua participação contribui para a análise
            da proposta de recomendação musical deste projeto acadêmico.
          </p>

          <div className="recommender-actions">
            <button
              className="form-button home-button recommender-back-button"
              onClick={() => navigate("/")}
            >
              Voltar para a tela inicial
            </button>

            <button
              className="form-button home-button recommender-submit-button"
              onClick={() => navigate("/recommender")}
            >
              Iniciar nova recomendação
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

        <div
          className="recommender-subtitle"
          style={{
            marginTop: "0.75rem",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            position: "relative",
            width: "fit-content",
          }}
        >
          <strong>Dúvidas sobre como avaliar? </strong>

          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              cursor: "help",
              position: "relative",
            }}
            className="evaluation-help-tooltip-wrapper"
          >
            <HelpCircle size={17} />

            <span
              className="evaluation-help-tooltip"
              style={{
                position: "absolute",
                left: "24px",
                top: "50%",
                transform: "translateY(-50%)",
                width: "260px",
                padding: "10px 12px",
                borderRadius: "8px",
                background: "#111827",
                color: "#ffffff",
                fontSize: "12px",
                lineHeight: "1.4",
                fontWeight: 400,
                opacity: 0,
                visibility: "hidden",
                transition: "opacity 0.15s ease-in-out",
                zIndex: 20,
                boxShadow: "0 6px 18px rgba(0, 0, 0, 0.22)",
              }}
            >
              Avalie de forma simples: notas maiores indicam que você gostou mais da
              música recomendada. Use notas menores quando a música não combinar com
              sua preferência.
            </span>
          </span>
        </div>

        <style>
          {`
            .evaluation-help-tooltip-wrapper:hover .evaluation-help-tooltip {
              opacity: 1 !important;
              visibility: visible !important;
            }
          `}
        </style>

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
          {displayedLists.map((listConfig) => (
            <section className="recommender-section" key={listConfig.displayLabel}>
              <h2 className="recommender-subtitle">{listConfig.displayLabel}</h2>

              <ul className="recommender-results-list">
                {listConfig.tracks.map((track, index) =>
                  renderTrackItem(track, index, listConfig.listType)
                )}
              </ul>
            </section>
          ))}
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
