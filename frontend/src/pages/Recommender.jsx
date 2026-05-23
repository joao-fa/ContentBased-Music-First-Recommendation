import { HelpCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import LoadingText from "../components/LoadingText";
import artistImage from "../assets/recommender/artist.png";
import songImage from "../assets/recommender/song.png";
import "../styles/Home.css";
import "../styles/Recommender.css";

const SEARCH_DEBOUNCE_MS = 300;
const MIN_SEARCH_CHARS = 2;
const MAX_VISIBLE_RESULTS = 40;

function normalizeSearchText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function rankCandidate(label, query) {
  const normalizedLabel = normalizeSearchText(label);
  const normalizedQuery = normalizeSearchText(query);

  if (!normalizedQuery) return 0;

  const index = normalizedLabel.indexOf(normalizedQuery);

  if (index === -1) return Number.POSITIVE_INFINITY;

  if (normalizedLabel === normalizedQuery) return 0;
  if (normalizedLabel.startsWith(normalizedQuery)) return 1;

  const words = normalizedLabel.split(" ");
  if (words.some((word) => word.startsWith(normalizedQuery))) return 2;

  return 3 + index / 1000;
}

function filterAndSortCandidates(items, query, getLabel) {
  const normalizedQuery = normalizeSearchText(query);

  if (!normalizedQuery) {
    return items.slice(0, MAX_VISIBLE_RESULTS);
  }

  return items
    .map((item) => {
      const label = getLabel(item);
      return {
        item,
        label,
        rank: rankCandidate(label, normalizedQuery),
      };
    })
    .filter(({ rank }) => Number.isFinite(rank))
    .sort((a, b) => {
      if (a.rank !== b.rank) return a.rank - b.rank;

      const aLabel = normalizeSearchText(a.label);
      const bLabel = normalizeSearchText(b.label);

      if (aLabel.length !== bLabel.length) {
        return aLabel.length - bLabel.length;
      }

      return aLabel.localeCompare(bLabel);
    })
    .slice(0, MAX_VISIBLE_RESULTS)
    .map(({ item }) => item);
}

function isCanceledRequest(err) {
  return (
    err?.name === "CanceledError" ||
    err?.code === "ERR_CANCELED" ||
    err?.message === "canceled"
  );
}

function DatabaseHelpTooltip({ variant = "track" }) {
  const isArtist = variant === "artist";

  const label = isArtist
    ? "Não encontrou seu artista ou banda?"
    : "Não encontrou sua música?";

  const ariaLabel = isArtist
    ? "Informações sobre a base de artistas e bandas"
    : "Informações sobre a base de músicas";

  const tooltipText = isArtist
    ? "O sistema possui uma base musical limitada, com músicas lançadas entre 1920 e 2023, contendo em torno de 600 mil músicas. Por isso, alguns artistas ou bandas podem não aparecer. Por favor, busque por um novo artista."
    : "O sistema possui uma base musical limitada, com músicas lançadas entre 1920 e 2023, contendo em torno de 600 mil músicas. Por favor, busque por uma nova música.";

  return (
    <div className="recommender-database-help">
      <span>{label}</span>

      <span
        className="recommender-database-tooltip-wrapper"
        tabIndex={0}
        aria-label={ariaLabel}
      >
        <HelpCircle size={17} />

        <span className="recommender-database-tooltip">
          {tooltipText}
        </span>
      </span>
    </div>
  );
}

function SearchTypeChooser({ searchType, onSelect }) {
  const options = [
    {
      value: "tracks",
      title: "Pesquisar por música",
      description: "Escolha uma música diretamente na base do sistema.",
      image: songImage,
      alt: "Ilustração de um disco de vinil representando busca por música",
    },
    {
      value: "artist",
      title: "Pesquisar por artista ou banda",
      description: "Encontre um artista ou banda e depois selecione uma de suas músicas.",
      image: artistImage,
      alt: "Ilustração de artista ou banda no palco representando busca por artista ou banda",
    },
  ];

  return (
    <section
      className={`recommender-type-chooser ${
        searchType ? "recommender-type-chooser-selected" : ""
      }`}
      aria-label="Escolha do tipo de pesquisa"
    >
      {options.map((option) => {
        const selected = searchType === option.value;

        return (
          <button
            key={option.value}
            type="button"
            className={`recommender-type-card ${selected ? "selected" : ""}`}
            onClick={() => onSelect(option.value)}
            aria-pressed={selected}
          >
            <img
              src={option.image}
              alt={option.alt}
              className="recommender-type-image"
            />

            <div className="recommender-type-card-body">
              <h2>{option.title}</h2>
              <p>{option.description}</p>
            </div>
          </button>
        );
      })}
    </section>
  );
}

export default function Recommender() {
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  const [searchType, setSearchType] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // ========== MODO TRACKS ==========
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTrack, setSelectedTrack] = useState(null);

  // ========== MODO ARTISTAS / BANDAS ==========
  const [artistQuery, setArtistQuery] = useState("");
  const [artistResults, setArtistResults] = useState([]);
  const [artistLoading, setArtistLoading] = useState(false);
  const [selectedArtist, setSelectedArtist] = useState(null);
  const [artistConfirmed, setArtistConfirmed] = useState(false);
  const [artistAllTracks, setArtistAllTracks] = useState([]);

  // ========== MODO FAIXAS DO ARTISTA / BANDA ==========
  const [artistTrackQuery, setArtistTrackQuery] = useState("");
  const [artistTrackResults, setArtistTrackResults] = useState([]);
  const [artistTrackLoading, setArtistTrackLoading] = useState(false);
  const [artistSelectedTrack, setArtistSelectedTrack] = useState(null);

  const errorRef = useRef(null);
  const searchInputRef = useRef(null);
  const trackSelectionRef = useRef(null);
  const artistTracksSectionRef = useRef(null);
  const artistTrackSelectionRef = useRef(null);

  const trimmedTrackQuery = useMemo(() => query.trim(), [query]);
  const trimmedArtistQuery = useMemo(() => artistQuery.trim(), [artistQuery]);
  const trimmedArtistTrackQuery = useMemo(
    () => artistTrackQuery.trim(),
    [artistTrackQuery]
  );

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

  const extractTrackInfo = (track) => {
    const id = track.id;
    const name = track.name || "";
    const artists = track.artists || "";
    const label = artists ? `${name} — ${artists}` : name;
    return { id, label };
  };

  const extractArtistInfo = (artist) => {
    const name = artist.name || artist.artist_name || artist;
    const id = artist.id || name;
    return { id, name };
  };

  const getTrackSearchLabel = (track) => {
    const { label } = extractTrackInfo(track);
    return label;
  };

  const getArtistSearchLabel = (artist) => {
    const { name } = extractArtistInfo(artist);
    return name;
  };

  useEffect(() => {
    if (errorMsg) {
      scrollToElement(errorRef.current);
    }
  }, [errorMsg]);

  useEffect(() => {
    if (searchType) {
      scrollToElement(searchInputRef.current);
    }
  }, [searchType]);

  const handleSearchTypeChange = (value) => {
    if (value === searchType) return;

    setSearchType(value);
    setErrorMsg("");

    setQuery("");
    setResults([]);
    setLoading(false);
    setSelectedTrack(null);

    setArtistQuery("");
    setArtistResults([]);
    setArtistLoading(false);
    setSelectedArtist(null);
    setArtistConfirmed(false);

    setArtistTrackQuery("");
    setArtistTrackResults([]);
    setArtistTrackLoading(false);
    setArtistSelectedTrack(null);
    setArtistAllTracks([]);
  };

  // ================== BUSCA AUTOMÁTICA DE TRACKS ==================
  useEffect(() => {
    if (searchType !== "tracks") return;

    setSelectedTrack(null);

    if (!trimmedTrackQuery) {
      setResults([]);
      setLoading(false);
      setErrorMsg("");
      return;
    }

    if (trimmedTrackQuery.length < MIN_SEARCH_CHARS) {
      setResults([]);
      setLoading(false);
      showErrorAndScroll(`Digite pelo menos ${MIN_SEARCH_CHARS} caracteres para buscar.`);
      return;
    }

    const controller = new AbortController();

    const timeoutId = window.setTimeout(async () => {
      setLoading(true);
      setErrorMsg("");

      try {
        const response = await api.get("/api/tracks/", {
          params: { q: trimmedTrackQuery },
          signal: controller.signal,
        });

        const data = Array.isArray(response.data)
          ? response.data
          : response.data.results || [];

        const filtered = filterAndSortCandidates(
          data,
          trimmedTrackQuery,
          getTrackSearchLabel
        );

        setResults(filtered);

        if (!filtered.length) {
          showErrorAndScroll(
            "Não encontramos essa música na base do sistema. Atualmente, a base contempla músicas lançadas entre 1920 e 2023."
          );
        }
      } catch (err) {
        if (isCanceledRequest(err)) return;

        console.error(err);
        setResults([]);
        showErrorAndScroll("Erro ao buscar músicas.");
      } finally {
        setLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [searchType, trimmedTrackQuery]);

  // ================== BUSCA AUTOMÁTICA DE ARTISTAS / BANDAS ==================
  useEffect(() => {
    if (searchType !== "artist") return;

    setSelectedArtist(null);
    setArtistConfirmed(false);
    setArtistAllTracks([]);
    setArtistTrackQuery("");
    setArtistTrackResults([]);
    setArtistSelectedTrack(null);

    if (!trimmedArtistQuery) {
      setArtistResults([]);
      setArtistLoading(false);
      setErrorMsg("");
      return;
    }

    if (trimmedArtistQuery.length < MIN_SEARCH_CHARS) {
      setArtistResults([]);
      setArtistLoading(false);
      showErrorAndScroll(`Digite pelo menos ${MIN_SEARCH_CHARS} caracteres para buscar.`);
      return;
    }

    const controller = new AbortController();

    const timeoutId = window.setTimeout(async () => {
      setArtistLoading(true);
      setErrorMsg("");

      try {
        const response = await api.get("/api/artists/", {
          params: { q: trimmedArtistQuery },
          signal: controller.signal,
        });

        const data = Array.isArray(response.data)
          ? response.data
          : response.data.results || [];

        const filtered = filterAndSortCandidates(
          data,
          trimmedArtistQuery,
          getArtistSearchLabel
        );

        setArtistResults(filtered);

        if (!filtered.length) {
          showErrorAndScroll(
            "Não encontramos esse artista ou banda na base do sistema. Atualmente, a base contempla músicas lançadas entre 1920 e 2023."
          );
        }
      } catch (err) {
        if (isCanceledRequest(err)) return;

        console.error(err);
        setArtistResults([]);
        showErrorAndScroll("Erro ao buscar artistas ou bandas.");
      } finally {
        setArtistLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [searchType, trimmedArtistQuery]);

  // ================== FILTRO AUTOMÁTICO DAS FAIXAS DO ARTISTA / BANDA ==================
  useEffect(() => {
    if (searchType !== "artist") return;
    if (!artistConfirmed) return;

    setArtistSelectedTrack(null);

    const filtered = filterAndSortCandidates(
      artistAllTracks,
      trimmedArtistTrackQuery,
      getTrackSearchLabel
    );

    setArtistTrackResults(filtered);

    if (artistAllTracks.length > 0 && trimmedArtistTrackQuery && !filtered.length) {
      showErrorAndScroll(
        "Nenhuma faixa desse artista ou banda corresponde ao texto digitado na base disponível."
      );
    } else {
      setErrorMsg("");
    }
  }, [
    searchType,
    artistConfirmed,
    artistAllTracks,
    trimmedArtistTrackQuery,
  ]);

  const handleSelectTrack = (track) => {
    if (!track?.id) {
      showErrorAndScroll("Track inválida.");
      return;
    }

    setSelectedTrack(track);
    setErrorMsg("");
    scrollToElement(trackSelectionRef.current);
  };

  const handleConfirmSelection = async () => {
    if (!selectedTrack) {
      showErrorAndScroll("Selecione uma música antes de continuar.");
      return;
    }

    setErrorMsg("");
    navigate("/recommendation-results", {
      state: {
        selected_track: selectedTrack,
      },
    });
  };

  const fetchArtistTracks = async (artistName) => {
    if (!artistName) return;

    setErrorMsg("");
    setArtistTrackLoading(true);

    try {
      const response = await api.get(
        `/api/artists/${encodeURIComponent(artistName)}/tracks/`,
        { params: { exact: true } }
      );

      const data = Array.isArray(response.data)
        ? response.data
        : response.data.results || [];

      const sortedData = filterAndSortCandidates(data, "", getTrackSearchLabel);

      setArtistAllTracks(data);
      setArtistTrackResults(sortedData);

      if (!data.length) {
        showErrorAndScroll(
          "Nenhuma faixa desse artista ou banda foi encontrada na base disponível."
        );
      }
    } catch (err) {
      console.error(err);
      setArtistAllTracks([]);
      setArtistTrackResults([]);
      showErrorAndScroll("Erro ao carregar faixas desse artista ou banda.");
    } finally {
      setArtistTrackLoading(false);
    }
  };

  const handleSelectArtist = async (artist) => {
    const { id, name } = extractArtistInfo(artist);
    const isAlreadySelected = selectedArtist?.id === id;

    if (isAlreadySelected) {
      setSelectedArtist(null);
      setArtistConfirmed(false);
      setArtistTrackQuery("");
      setArtistSelectedTrack(null);
      setArtistAllTracks([]);
      setArtistTrackResults([]);
      setErrorMsg("");
      return;
    }

    setSelectedArtist({ id, name });
    setArtistConfirmed(true);
    setArtistTrackQuery("");
    setArtistSelectedTrack(null);
    setArtistAllTracks([]);
    setArtistTrackResults([]);
    setErrorMsg("");

    await fetchArtistTracks(name);
    scrollToElement(artistTracksSectionRef.current);
  };

  const handleSelectArtistTrack = (track) => {
    if (!track?.id) {
      showErrorAndScroll("Track inválida.");
      return;
    }

    setArtistSelectedTrack(track);
    setErrorMsg("");
    scrollToElement(artistTrackSelectionRef.current);
  };

  const handleConfirmArtistTrackSelection = async () => {
    if (!artistSelectedTrack) {
      showErrorAndScroll("Selecione uma faixa antes de continuar.");
      return;
    }

    setErrorMsg("");
    navigate("/recommendation-results", {
      state: {
        selected_track: artistSelectedTrack,
      },
    });
  };

  const preventManualSubmit = (e) => {
    e.preventDefault();
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

      <main className="form-container recommender-container">
        <h1 className="recommender-title">Nova Recomendação</h1>

        <p className="recommender-description">
          Para gerar suas recomendações, precisamos escolher uma música de seu gosto. Primeiro, escolha um tipo de pesquisa.
        </p>

        <SearchTypeChooser
          searchType={searchType}
          onSelect={handleSearchTypeChange}
        />

        {searchType && (
          <>
            {errorMsg && (
              <p ref={errorRef} className="recommender-error" tabIndex={-1}>
                {errorMsg}
              </p>
            )}

            {searchType === "tracks" && (
              <>
                <div className="recommender-search-row">
                  <form className="recommender-form" onSubmit={preventManualSubmit}>
                    <input
                      type="text"
                      placeholder="Digite o nome da música..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      ref={searchInputRef}
                      className="recommender-input"
                      autoComplete="off"
                    />
                  </form>

                  <DatabaseHelpTooltip variant="track" />
                </div>

                <div className="recommender-results">
                  {loading && (
                    <p className="recommender-empty"><LoadingText label="Buscando músicas" /></p>
                  )}

                  {!loading && results.length > 0 && (
                    <ul className="recommender-results-list">
                      {results.map((track) => {
                        const { id, label } = extractTrackInfo(track);
                        const selected = selectedTrack?.id === id;

                        return (
                          <li
                            key={id}
                            className={`recommender-result-item ${selected ? "selected" : ""}`}
                            onClick={() => handleSelectTrack(track)}
                          >
                            <span className="track-label">{label}</span>
                            {selected && (
                              <span className="track-selected-badge">Selecionada</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}

                  {!trimmedTrackQuery && !loading && (
                    <p className="recommender-empty">
                      Digite uma música para iniciar a busca.
                    </p>
                  )}
                </div>

                <div className="recommender-selection" ref={trackSelectionRef}>
                  <p>
                    Música selecionada:{" "}
                    {selectedTrack ? (
                      <strong>
                        {selectedTrack.name} — {selectedTrack.artists}
                      </strong>
                    ) : (
                      <span>Nenhuma música selecionada.</span>
                    )}
                  </p>

                  <button
                    type="button"
                    className={`form-button home-button recommender-confirm-button ${!selectedTrack ? "button-disabled-state" : ""}`}
                    onClick={handleConfirmSelection}
                    disabled={loading}
                    aria-disabled={!selectedTrack || loading}
                  >
                    {loading ? <LoadingText label="Aguarde" /> : "Confirmar seleção"}
                  </button>
                </div>
              </>
            )}

            {searchType === "artist" && (
              <>
                <section className="recommender-artist-section">
                  <h2 className="recommender-subtitle">
                    1. Selecione um artista ou banda
                  </h2>

                  <div className="recommender-search-row">
                    <form className="recommender-form" onSubmit={preventManualSubmit}>
                      <input
                        type="text"
                        placeholder="Digite o nome do artista ou banda..."
                        value={artistQuery}
                        onChange={(e) => setArtistQuery(e.target.value)}
                        ref={searchInputRef}
                        className="recommender-input"
                        autoComplete="off"
                      />
                    </form>

                    <DatabaseHelpTooltip variant="artist" />
                  </div>

                  <p className="recommender-search-helper">
                    A lista de artistas e bandas é atualizada automaticamente conforme você digita.
                  </p>

                  <div className="recommender-results">
                    {artistLoading && (
                      <p className="recommender-empty"><LoadingText label="Buscando artistas ou bandas" /></p>
                    )}

                    {!artistLoading && artistResults.length > 0 && (
                      <ul className="recommender-results-list">
                        {artistResults.map((artist, idx) => {
                          const { id, name } = extractArtistInfo(artist);
                          const key = id || `${name}-${idx}`;
                          const selected = selectedArtist?.id === id;

                          return (
                            <li
                              key={key}
                              className={`recommender-result-item ${selected ? "selected" : ""}`}
                              onClick={() => handleSelectArtist(artist)}
                            >
                              <span className="track-label">{name}</span>
                              {selected && (
                                <span className="track-selected-badge">Selecionado</span>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    )}

                    {!trimmedArtistQuery && !artistLoading && (
                      <p className="recommender-empty">
                        Digite um artista ou banda para iniciar a busca.
                      </p>
                    )}
                  </div>

                  <div className="recommender-selection">
                    <p>
                      Artista ou banda selecionado(a):{" "}
                      {selectedArtist ? (
                        <strong>{selectedArtist.name}</strong>
                      ) : (
                        <span>Nenhum artista ou banda selecionado(a).</span>
                      )}
                    </p>

                    {selectedArtist && (
                      <p className="recommender-search-helper">
                        Clique novamente no artista ou banda selecionado(a) para desfazer a seleção.
                      </p>
                    )}
                  </div>
                </section>

                {artistConfirmed && selectedArtist && (
                  <section className="recommender-artist-tracks-section" ref={artistTracksSectionRef}>
                    <h2 className="recommender-subtitle">
                      2. Selecione uma música de {selectedArtist.name}
                    </h2>

                    <p className="recommender-search-helper">
                      Deixe o campo vazio para ver todas as faixas do artista ou digite
                      para filtrar progressivamente.
                    </p>

                    <div className="recommender-search-row">
                      <form className="recommender-form" onSubmit={preventManualSubmit}>
                        <input
                          type="text"
                          placeholder="Digite o nome da música..."
                          value={artistTrackQuery}
                          onChange={(e) => setArtistTrackQuery(e.target.value)}
                          className="recommender-input"
                          autoComplete="off"
                          disabled={artistTrackLoading}
                        />
                      </form>

                      <DatabaseHelpTooltip variant="track" />
                    </div>

                    <div className="recommender-results">
                      {artistTrackLoading && (
                        <p className="recommender-empty">
                          <LoadingText label="Carregando faixas do artista ou banda" />
                        </p>
                      )}

                      {!artistTrackLoading && artistTrackResults.length > 0 && (
                        <ul className="recommender-results-list">
                          {artistTrackResults.map((track) => {
                            const { id, label } = extractTrackInfo(track);
                            const selected = artistSelectedTrack?.id === id;

                            return (
                              <li
                                key={id}
                                className={`recommender-result-item ${selected ? "selected" : ""}`}
                                onClick={() => handleSelectArtistTrack(track)}
                              >
                                <span className="track-label">{label}</span>
                                {selected && (
                                  <span className="track-selected-badge">Selecionada</span>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      )}

                      {!artistTrackLoading &&
                        artistAllTracks.length > 0 &&
                        artistTrackResults.length === 0 && (
                          <p className="recommender-empty">
                            Nenhuma faixa desse artista ou banda corresponde ao texto digitado na base disponível.
                          </p>
                        )}
                    </div>

                    <div className="recommender-selection" ref={artistTrackSelectionRef}>
                      <p>
                        Música selecionada:{" "}
                        {artistSelectedTrack ? (
                          <strong>
                            {artistSelectedTrack.name} — {artistSelectedTrack.artists}
                          </strong>
                        ) : (
                          <span>Nenhuma música selecionada.</span>
                        )}
                      </p>

                      <button
                        type="button"
                        className={`form-button home-button recommender-confirm-button ${!artistSelectedTrack ? "button-disabled-state" : ""}`}
                        onClick={handleConfirmArtistTrackSelection}
                        disabled={loading}
                        aria-disabled={!artistSelectedTrack || loading}
                      >
                        {loading ? <LoadingText label="Aguarde" /> : "Confirmar seleção"}
                      </button>
                    </div>
                  </section>
                )}
              </>
            )}
          </>
        )}
      </main>

      <footer className="home-footer">
        <div className="footer-content">
          <p className="footer-text">
            Projeto acadêmico desenvolvido para pesquisa em sistemas de recomendação musical
            baseados em conteúdo. Consulte as referências na aba 'Referências'.
          </p>
          <p className="footer-info">
            © {new Date().getFullYear()} João Víctor Ferreira Araujo — Universidade de São
            Paulo (EACH-USP)
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
