import { HelpCircle, Play } from "lucide-react";
import { FaSpotify } from "react-icons/fa";
import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import returnImage from "../assets/recommender/return.png";
import referencesImage from "../assets/references/profile.png";
import myRecommendationsImage from "../assets/recommender/my_recommendations.png";
import newRecommendationImage from "../assets/recommender/new_recommendation.png";
import "../styles/Home.css";
import "../styles/Recommender.css";
import api from "../api";

const RANDOM_LIST_TYPE = "randomList";
const GREATEST_VARIATION_LIST_TYPE = "greatestVariationList";
const FURTHEST_FROM_THE_MEDIAN_LIST_TYPE = "furthestFromTheMedianList";

const MOBILE_RECOMMENDATION_TUTORIAL_MEDIA_QUERY = "(max-width: 700px)";

const recommendationTutorialVideoModules = import.meta.glob(
  "../assets/recommender/*.mp4",
  { eager: true, query: "?url", import: "default" }
);

const getRecommendationTutorialVideoSrc = (filename) =>
  recommendationTutorialVideoModules[`../assets/recommender/${filename}`] ??
  `/src/assets/recommender/${filename}`;

const recommendationTutorialVideos = [
  {
    title: "Poderá ouvir uma prévia da música recomendada",
    desktopFilename: "scene_1.mp4",
    mobileFilename: "mobile_scene_1.mp4",
  },
  {
    title: "Poderá abrir a música diretamente pelo Spotify para ouvir na íntegra",
    desktopFilename: "scene_2.mp4",
    mobileFilename: "mobile_scene_2.mp4",
  },
  {
    title: "Precisará avaliar cada uma das músicas recomendadas",
    desktopFilename: "scene_3.mp4",
    mobileFilename: "mobile_scene_3.mp4",
  },
];

function CompletionActionChooser({ onNavigate }) {
  const actions = [
    {
      title: "Voltar para a tela inicial",
      description: "Retorne para a página principal do sistema.",
      image: returnImage,
      alt: "Ilustração representando retorno para a tela inicial",
      path: "/",
    },
    {
      title: "Acessar referências",
      description: "Consulte mais informações sobre o projeto, autor e orientadores.",
      image: referencesImage,
      imageClass: "recommendation-completion-card-image-references",
      alt: "Imagem representando a página de referências",
      path: "/references",
    },
    {
      title: "Conferir suas recomendações",
      description: "Veja o histórico das recomendações que você já avaliou.",
      image: myRecommendationsImage,
      alt: "Ilustração representando minhas recomendações",
      path: "/my-recommendations",
    },
    {
      title: "Nova recomendação",
      description: "Inicie uma nova busca e avalie novas recomendações.",
      image: newRecommendationImage,
      alt: "Ilustração representando uma nova recomendação",
      path: "/recommender",
    },
  ];

  return (
    <section
      className="recommendation-completion-actions"
      aria-label="Ações após avaliação concluída"
    >
      {actions.map((action) => (
        <button
          key={action.path}
          type="button"
          className="recommendation-completion-card"
          onClick={() => onNavigate(action.path)}
        >
          <div className="recommendation-completion-card-image-frame">
            <img
              src={action.image}
              alt={action.alt}
              className={`recommendation-completion-card-image ${action.imageClass || ""}`.trim()}
            />
          </div>

          <div className="recommendation-completion-card-body">
            <h2>{action.title}</h2>
            <p>{action.description}</p>
          </div>
        </button>
      ))}
    </section>
  );
}

export default function RecommendationResults() {
  const location = useLocation();
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const data = location.state;

  const {
    selected_track,
    random_list,
    variable_based_list,
    variable_based_strategy,
    used_feature,
    primary_metric,
    secondary_metric,
    used_features,
    reference_feature_value,
    reference_feature_median,
    reference_feature_std_deviation,
    reference_distance_from_median,
    cluster_metadata_snapshot,
    cluster,
  } = data || {};

  const resolvedVariableBasedStrategy =
    variable_based_strategy === FURTHEST_FROM_THE_MEDIAN_LIST_TYPE
      ? FURTHEST_FROM_THE_MEDIAN_LIST_TYPE
      : GREATEST_VARIATION_LIST_TYPE;

  const primaryMetric = primary_metric ?? used_features?.[0]?.feature ?? used_feature ?? null;
  const secondaryMetric = secondary_metric ?? used_features?.[1]?.feature ?? null;

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
      listType: RANDOM_LIST_TYPE,
      tracks: initialRandomList,
    };

    const variableBasedListConfig = {
      displayLabel: shouldShowRandomFirst ? "Lista 2" : "Lista 1",
      listType: resolvedVariableBasedStrategy,
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
      randomList: initialRandomList,
      variableBasedList: initialVariableBasedList,
      variableBasedStrategy: resolvedVariableBasedStrategy,
      displayedLists,
      displayOrderConfig,
    };
  }

  const randomList = frozenListsRef.current?.randomList ?? [];
  const variableBasedList = frozenListsRef.current?.variableBasedList ?? [];
  const displayedLists = frozenListsRef.current?.displayedLists ?? [];
  const displayOrderConfig = frozenListsRef.current?.displayOrderConfig ?? {};
  const frozenVariableBasedStrategy =
    frozenListsRef.current?.variableBasedStrategy ?? resolvedVariableBasedStrategy;

  const [ratings, setRatings] = useState({});
  const [errorMsg, setErrorMsg] = useState("");
  const [openEmbedTrackKey, setOpenEmbedTrackKey] = useState(null);

  const [previewOpenedTracks, setPreviewOpenedTracks] = useState({});
  const [spotifyOpenedTracks, setSpotifyOpenedTracks] = useState({});

  const [showLanguageQuestion, setShowLanguageQuestion] = useState(false);
  const [languageHadImpact, setLanguageHadImpact] = useState(null);
  const [languageImpactedTracks, setLanguageImpactedTracks] = useState({});

  const [evaluationSubmitted, setEvaluationSubmitted] = useState(false);
  const [showRecommendationIntro, setShowRecommendationIntro] = useState(true);
  const [useMobileTutorialVideos, setUseMobileTutorialVideos] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;

    return window.matchMedia(MOBILE_RECOMMENDATION_TUTORIAL_MEDIA_QUERY).matches;
  });

  const errorRef = useRef(null);
  const languageQuestionRef = useRef(null);
  const recommendationListsRef = useRef(null);

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

  const selectedRecommendationTutorialVideos = useMemo(() => {
    return recommendationTutorialVideos.map((video) => ({
      title: video.title,
      src: getRecommendationTutorialVideoSrc(
        useMobileTutorialVideos ? video.mobileFilename : video.desktopFilename
      ),
    }));
  }, [useMobileTutorialVideos]);

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

  const scrollToElement = (element) => {
    if (!element) return;

    window.requestAnimationFrame(() => {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };

  const showErrorAndScroll = (message) => {
    setErrorMsg(message);
    scrollToElement(errorRef.current);
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

  const allRatingsComplete = allDisplayedTracks.every((item) => {
    const trackKey = getTrackKey(item.t, item.idx, item.listType);
    const value = ratings[trackKey];
    return value !== undefined && value !== "";
  });

  const hasLanguageImpactSelection =
    languageHadImpact === false ||
    (languageHadImpact === true &&
      Object.values(languageImpactedTracks).some(Boolean));

  const canSubmitEvaluation = showLanguageQuestion
    ? allRatingsComplete && hasLanguageImpactSelection
    : allRatingsComplete;

  useLayoutEffect(() => {
    if (showRecommendationIntro && typeof window !== "undefined") {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }
  }, [showRecommendationIntro]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;

    const mediaQuery = window.matchMedia(MOBILE_RECOMMENDATION_TUTORIAL_MEDIA_QUERY);
    const updateTutorialVideoMode = (event) => {
      setUseMobileTutorialVideos(event.matches);
    };

    setUseMobileTutorialVideos(mediaQuery.matches);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", updateTutorialVideoMode);
      return () => mediaQuery.removeEventListener("change", updateTutorialVideoMode);
    }

    mediaQuery.addListener(updateTutorialVideoMode);
    return () => mediaQuery.removeListener(updateTutorialVideoMode);
  }, []);

  useEffect(() => {
    if (errorMsg) {
      scrollToElement(errorRef.current);
    }
  }, [errorMsg]);

  useEffect(() => {
    if (showLanguageQuestion) {
      scrollToElement(languageQuestionRef.current);
    }
  }, [showLanguageQuestion]);

  const validateRatings = () => {
    for (const item of allDisplayedTracks) {
      const trackKey = getTrackKey(item.t, item.idx, item.listType);
      const value = ratings[trackKey];

      if (value === undefined || value === "") {
        showErrorAndScroll("Preencha todas as notas (0 a 10) antes de prosseguir.");
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
      scrollToElement(languageQuestionRef.current);
      return;
    }

    if (languageHadImpact === null) {
      showErrorAndScroll("Informe se o idioma da música influenciou negativamente sua avaliação.");
      return;
    }

    if (
      languageHadImpact === true &&
      !Object.values(languageImpactedTracks).some(Boolean)
    ) {
      showErrorAndScroll("Selecione pelo menos uma música impactada pelo idioma.");
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
          used_features: used_features ?? [],
          primary_metric: primaryMetric,
          secondary_metric: secondaryMetric,
          reference_feature_value: reference_feature_value ?? null,
          reference_feature_median: reference_feature_median ?? null,
          reference_feature_std_deviation: reference_feature_std_deviation ?? null,
          reference_distance_from_median: reference_distance_from_median ?? null,
          variable_based_strategy: frozenVariableBasedStrategy,
          cluster: cluster ?? selected_track?.cluster ?? null,
          cluster_metadata_snapshot: cluster_metadata_snapshot ?? null,
          random_list_size: randomList.length,
          variable_based_list_size: variableBasedList.length,
          display_order: displayOrderConfig,
        },

        base_track_id: selected_track?.id,
        used_feature: used_feature ?? null,
        primary_metric: primaryMetric,
        secondary_metric: secondaryMetric,

        base_track_name: selected_track?.name ?? "",
        base_track_artists: selected_track?.artists ?? "",
        recommendation_cluster: selected_track?.cluster ?? null,

        items: [
          ...randomList.map((track, index) => {
            const trackKey = getTrackKey(track, index, RANDOM_LIST_TYPE);

            return {
              track_id: track.id,
              order_in_list: index + 1,
              list_type: RANDOM_LIST_TYPE,
              rating: Number(ratings[trackKey]),
              language_influenced_rating:
                languageHadImpact === true &&
                Boolean(languageImpactedTracks[trackKey]),
              primary_metric: null,
              secondary_metric: null,
              recommendation_cluster: track.cluster ?? null,
              base_track_feature_value: null,
              recommended_track_feature_value: null,
              was_preview_opened: Boolean(previewOpenedTracks[trackKey]),
              spotify_opened: Boolean(spotifyOpenedTracks[trackKey]),
              recommended_track_name: track.name ?? "",
              recommended_track_artists: track.artists ?? "",
            };
          }),

          ...variableBasedList.map((track, index) => {
            const trackKey = getTrackKey(track, index, frozenVariableBasedStrategy);

            return {
              track_id: track.id,
              order_in_list: index + 1,
              list_type: frozenVariableBasedStrategy,
              rating: Number(ratings[trackKey]),
              language_influenced_rating:
                languageHadImpact === true &&
                Boolean(languageImpactedTracks[trackKey]),
              primary_metric: primaryMetric,
              secondary_metric: secondaryMetric,
              recommendation_cluster: track.cluster ?? null,
              base_track_feature_value:
                reference_feature_value ?? getFeatureValue(selected_track, primaryMetric),
              recommended_track_feature_value: getFeatureValue(track, primaryMetric),
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
      showErrorAndScroll(
        "Erro ao salvar a avaliação. Por favor, tente novamente mais tarde ou entre em contato com o Administrador."
      );
    }
  };

  const handleBackToRecommender = () => {
    navigate("/recommender");
  };

  const handleBackToRecommendationIntro = () => {
    setShowRecommendationIntro(true);
  };

  const handleAdvanceToRecommendations = () => {
    clientStartedAtRef.current = new Date().toISOString();
    setShowRecommendationIntro(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
      <li
        key={trackKey}
        className={`recommender-result-item rating-item ${
          showLanguageQuestion && languageHadImpact === true
            ? "language-impact-selectable"
            : ""
        }`}
      >
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
          <label className="language-impact-checkbox language-impact-checkbox-attention">
            <input
              type="checkbox"
              checked={Boolean(languageImpactedTracks[trackKey])}
              onChange={() => toggleLanguageImpactTrack(trackKey)}
            />
            O idioma desta música influenciou negativamente minha avaliação
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

        <main className="form-container recommender-container recommendation-completion-container">
          <h1 className="recommender-title">Avaliação concluída</h1>

          <p className="recommender-subtitle recommendation-completion-text">
            Obrigado por submeter sua avaliação. Sua participação contribui para a análise
            da proposta de recomendação musical deste projeto acadêmico. Quanto mais análises
            você fizer, mais você me ajuda a comparar as estratégias e entender melhor os
            resultados do sistema.
          </p>

          <h2 className="recommendation-completion-question">
            O que deseja fazer agora?
          </h2>

          <CompletionActionChooser onNavigate={navigate} />
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

  if (showRecommendationIntro) {
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

        <main className="form-container recommender-container recommendation-intro-container">
          <h1 className="recommender-title">Na próxima página você:</h1>

          <section
            className="recommendation-intro-videos"
            aria-label="Demonstração das ações disponíveis nas recomendações"
          >
            {selectedRecommendationTutorialVideos.map((video, index) => (
              <article className="recommendation-intro-video-card" key={video.src}>
                <h2 className="recommendation-intro-video-title">
                  {index + 1}. {video.title}
                </h2>

                <video
                  className="recommendation-intro-video"
                  src={video.src}
                  autoPlay
                  loop
                  muted
                  playsInline
                  preload="auto"
                >
                  Seu navegador não suporta a reprodução deste vídeo.
                </video>
              </article>
            ))}
          </section>

          <div className="recommender-actions recommendation-intro-actions">
            <button
              className="form-button home-button recommender-back-button"
              onClick={handleBackToRecommender}
            >
              Voltar
            </button>

            <button
              className="form-button home-button recommender-submit-button"
              onClick={handleAdvanceToRecommendations}
            >
              Avançar
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
        <h1 className="recommender-title">Avalie as Recomendações de acordo com seu gosto</h1>

        <div className="recommendation-results-intro-row">
          <p className="recommender-subtitle recommendation-results-target">
            Recomendações geradas para{" "}
            <strong>{selected_track?.name || "a música selecionada"}</strong>
          </p>

          <div className="recommender-database-help recommendation-evaluation-help">
            <span>Dúvidas sobre como avaliar?</span>

            <span
              className="recommender-database-tooltip-wrapper"
              tabIndex={0}
              aria-label="Informações sobre como avaliar recomendações"
            >
              <HelpCircle size={17} />

              <span className="recommender-database-tooltip recommendation-evaluation-tooltip">
                Avalie de forma simples: notas maiores indicam que você gostou mais da
                música recomendada. Use notas menores quando a música não combinar com
                sua preferência.
              </span>
            </span>
          </div>
        </div>

        {errorMsg && (
          <div
            ref={errorRef}
            tabIndex={-1}
            className="recommendation-error-card"
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

        <div className="recommender-lists-grid" ref={recommendationListsRef}>
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

        <p className="recommendation-honesty-note">
          Por favor, seja honesta(o).{" "}
          <strong>Avaliações negativas ou positivas colaboram igualmente para o projeto.</strong>
        </p>

        {showLanguageQuestion && (
          <section className="language-impact-card" ref={languageQuestionRef}>
            <h2 className="recommender-subtitle">
              O idioma da música influenciou negativamente sua avaliação?
            </h2>

            <div className="language-impact-options">
              <label>
                <input
                  type="radio"
                  name="languageImpact"
                  checked={languageHadImpact === true}
                  onChange={() => {
                    setLanguageHadImpact(true);
                    scrollToElement(recommendationListsRef.current);
                  }}
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
                Marque a caixa nas músicas em que o idioma impactou negativamente em sua nota.
              </p>
            )}
          </section>
        )}

        <div className="recommender-actions">
          <button
            className="form-button home-button recommender-back-button"
            onClick={handleBackToRecommendationIntro}
          >
            Voltar
          </button>

          <button
            className={`form-button home-button recommender-submit-button ${!canSubmitEvaluation ? "button-disabled-state" : ""}`}
            onClick={submitEvaluation}
            aria-disabled={!canSubmitEvaluation}
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
