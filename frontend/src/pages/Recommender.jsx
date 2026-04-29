import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import "../styles/Home.css";
import "../styles/Recommender.css";

export default function Recommender() {
  const navigate = useNavigate();
  const username = localStorage.getItem("USERNAME") || "Usuário";

  // Tipo de pesquisa
  const [searchType, setSearchType] = useState("tracks");
  const [errorMsg, setErrorMsg] = useState("");

  // ========== MODO TRACKS ==========
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  // Agora salva o objeto completo da track:
  const [selectedTrack, setSelectedTrack] = useState(null);

  // ========== MODO ARTIST (etapa 1) ==========
  const [artistQuery, setArtistQuery] = useState("");
  const [artistResults, setArtistResults] = useState([]);
  const [artistLoading, setArtistLoading] = useState(false);
  const [selectedArtist, setSelectedArtist] = useState(null);
  const [artistConfirmed, setArtistConfirmed] = useState(false);
  const [artistAllTracks, setArtistAllTracks] = useState([]);

  // ========== MODO ARTIST (etapa 2) ==========
  const [artistTrackQuery, setArtistTrackQuery] = useState("");
  const [artistTrackResults, setArtistTrackResults] = useState([]);
  const [artistTrackLoading, setArtistTrackLoading] = useState(false);
  const [artistSelectedTrack, setArtistSelectedTrack] = useState(null);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  // Reset ao mudar o tipo
  const handleSearchTypeChange = (value) => {
    setSearchType(value);
    setErrorMsg("");

    setQuery("");
    setResults([]);
    setSelectedTrack(null);

    setArtistQuery("");
    setArtistResults([]);
    setSelectedArtist(null);
    setArtistConfirmed(false);
    setArtistTrackQuery("");
    setArtistTrackResults([]);
    setArtistSelectedTrack(null);
  };

  const extractTrackInfo = (track) => {
    const id = track.id;
    const name = track.name;
    const artists = track.artists || "";
    const label = artists ? `${name} — ${artists}` : name;
    return { id, label };
  };

  const extractArtistInfo = (artist) => {
    const name = artist.name || artist.artist_name || artist;
    const id = artist.id || name;
    return { id, name };
  };

  // ================== BUSCA DE TRACKS ==================
  const handleSearch = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setResults([]);
    setSelectedTrack(null);

    if (!query.trim()) {
      setErrorMsg("Digite um termo para buscar.");
      return;
    }

    setLoading(true);
    try {
      const response = await api.get("/api/tracks/", {
        params: { q: query.trim() },
      });

      const data = Array.isArray(response.data)
        ? response.data
        : response.data.results || [];

      if (!data.length) {
        setErrorMsg("Nenhum resultado encontrado.");
      }

      setResults(data);
    } catch (err) {
      console.error(err);
      setErrorMsg("Erro ao buscar músicas.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTrack = (track) => {
    if (!track?.id) {
      setErrorMsg("Track inválida.");
      return;
    }
    setSelectedTrack(track);
  };

  // ================== CONFIRMAR TRACK — chama o endpoint intermediário ==================
  const handleConfirmSelection = async () => {
    if (!selectedTrack) {
      setErrorMsg("Selecione uma música antes de continuar.");
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/api/recommend/", { track: { id: selectedTrack.id } });

      navigate("/recommendation-results", { state: response.data });

    } catch (err) {
      console.error(err);
      setErrorMsg("Erro ao gerar recomendações. Por favor, tente novamente mais tarde ou entre em contato com o Administrador.");
    } finally {
      setLoading(false);
    }
  };

  // ================== ARTISTA — ETAPA 1 ==================
  const handleArtistSearch = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setArtistResults([]);
    setSelectedArtist(null);
    setArtistConfirmed(false);

    if (!artistQuery.trim()) {
      setErrorMsg("Digite o nome de um artista.");
      return;
    }

    setArtistLoading(true);
    try {
      const response = await api.get("/api/artists/", {
        params: { q: artistQuery.trim() },
      });

      const data = Array.isArray(response.data)
        ? response.data
        : response.data.results || [];

      if (!data.length) {
        setErrorMsg("Nenhum artista encontrado.");
      }

      setArtistResults(data);
    } catch (err) {
      console.error(err);
      setErrorMsg("Erro ao buscar artistas.");
    } finally {
      setArtistLoading(false);
    }
  };

  const handleSelectArtist = async (artist) => {
    const { id, name } = extractArtistInfo(artist);

    setSelectedArtist({ id, name });

    setArtistConfirmed(true);

    setArtistTrackQuery("");
    setArtistSelectedTrack(null);
    setArtistAllTracks([]);
    setArtistTrackResults([]);

    await fetchArtistTracks(name);
  };

  const handleConfirmArtist = () => {
    if (!selectedArtist) {
      setErrorMsg("Selecione um artista primeiro.");
      return;
    }

    setArtistConfirmed(true);
    setArtistTrackQuery("");
    setArtistTrackResults([]);
    setArtistSelectedTrack(null);
  };

  // ================== ARTISTA — ETAPA 2 ==================
  const handleArtistTrackSearch = async (e) => {
    e.preventDefault();

    if (!selectedArtist?.name) {
      setErrorMsg("Selecione um artista antes.");
      return;
    }

    const q = artistTrackQuery.trim().toLowerCase();

    if (!q) {
      setArtistTrackResults(artistAllTracks);
      setErrorMsg("");
      return;
    }

    const filtered = artistAllTracks.filter((t) => {
      const name = (t.name || "").toLowerCase();
      const artists = (t.artists || "").toLowerCase();
      return name.includes(q) || artists.includes(q);
    });

    setArtistTrackResults(filtered);

    if (!filtered.length) {
      setErrorMsg("Nenhuma música encontrada para esse artista.");
    } else {
      setErrorMsg("");
    }
  };

  const handleSelectArtistTrack = (track) => {
    if (!track?.id) {
      setErrorMsg("Track inválida.");
      return;
    }
    setArtistSelectedTrack(track);
  };

  const handleConfirmArtistTrackSelection = async () => {
    if (!artistSelectedTrack) {
      setErrorMsg("Selecione uma faixa antes de continuar.");
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/api/recommend/", { track: { id: artistSelectedTrack.id } });

      navigate("/recommendation-results", { state: response.data });

    } catch (err) {
      console.error(err);
      setErrorMsg("Erro ao gerar recomendações. Por favor, tente novamente mais tarde ou entre em contato com o Administrador.");
    } finally {
      setLoading(false);
    }
  };

  const fetchArtistTracks = async (artistName) => {
  if (!artistName) return;

  setErrorMsg("");
  setArtistTrackLoading(true);

  try {
    const response = await api.get(
      `/api/artists/${encodeURIComponent(artistName)}/tracks/`
    );

    const data = Array.isArray(response.data)
      ? response.data
      : response.data.results || [];

    setArtistAllTracks(data);
    setArtistTrackResults(data);

    if (!data.length) {
      setErrorMsg("Nenhuma música encontrada para esse artista.");
    }
  } catch (err) {
    console.error(err);
    setErrorMsg("Erro ao carregar faixas desse artista.");
  } finally {
    setArtistTrackLoading(false);
  }
};

  // ===========================================================
  // =============== RENDERIZAÇÃO DA PÁGINA =====================
  // ===========================================================

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
        <h1 className="recommender-title">Nova Recomendação</h1>

        <p className="recommender-description">
          Escolha um tipo de pesquisa abaixo e então selecione uma música de sua preferência.
        </p>

        {/* Tipo de busca */}
        <div className="recommender-search-type">
          <label htmlFor="searchType">Tipo de pesquisa:</label>
          <select
            id="searchType"
            value={searchType}
            onChange={(e) => handleSearchTypeChange(e.target.value)}
          >
            <option value="tracks">Por música</option>
            <option value="artist">Por artista</option>
          </select>
        </div>

        {errorMsg && <p className="recommender-error">{errorMsg}</p>}

        {/* ================== BLOCO TRACKS ================== */}
        {searchType === "tracks" && (
          <>
            <form className="recommender-form" onSubmit={handleSearch}>
              <input
                type="text"
                placeholder="Digite o nome da música..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="recommender-input"
              />
              <button
                type="submit"
                className="form-button home-button recommender-search-button"
                disabled={loading}
              >
                {loading ? "Buscando..." : "Buscar"}
              </button>
            </form>

            <div className="recommender-results">
              {results.length > 0 && (
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
                        {selected && <span className="track-selected-badge">Selecionada</span>}
                      </li>
                    );
                  })}
                </ul>
              )}

              {results.length === 0 && !loading && (
                <p className="recommender-empty">Nenhuma busca realizada ainda.</p>
              )}
            </div>

            <div className="recommender-selection">
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
                className="form-button home-button recommender-confirm-button"
                onClick={handleConfirmSelection}
                disabled={!selectedTrack}
              >
                Confirmar seleção
              </button>
            </div>
          </>
        )}

        {/* ================== BLOCO ARTIST ================== */}
        {searchType === "artist" && (
          <>
            {/* === Etapa 1 === */}
            <section className="recommender-artist-section">
              <h2 className="recommender-subtitle">1. Selecione um artista</h2>

              <form className="recommender-form" onSubmit={handleArtistSearch}>
                <input
                  type="text"
                  placeholder="Digite o nome do artista..."
                  value={artistQuery}
                  onChange={(e) => setArtistQuery(e.target.value)}
                  className="recommender-input"
                />

                <button
                  type="submit"
                  className="form-button home-button recommender-search-button"
                  disabled={artistLoading}
                >
                  {artistLoading ? "Buscando..." : "Buscar"}
                </button>
              </form>

              <div className="recommender-results">
                {artistResults.length > 0 && (
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
                          {selected && <span className="track-selected-badge">Selecionado</span>}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <div className="recommender-selection">
                <p>
                  Artista selecionado:{" "}
                  {selectedArtist ? (
                    <strong>{selectedArtist.name}</strong>
                  ) : (
                    <span>Nenhum artista selecionado.</span>
                  )}
                </p>

                <button
                  type="button"
                  className="form-button home-button recommender-confirm-button"
                  onClick={handleConfirmArtist}
                  disabled={!selectedArtist}
                >
                  Confirmar artista
                </button>
              </div>
            </section>

            {/* === Etapa 2 === */}
            {artistConfirmed && (
              <section className="recommender-artist-tracks-section">
                <h2 className="recommender-subtitle">
                  2. Busque uma música de {selectedArtist.name}
                </h2>
                <h5 className="recommender-subtitle">
                  Clique em filtrar com a caixa vazia para exibir todas as faixas do seu artista.
                </h5>

                <form className="recommender-form" onSubmit={handleArtistTrackSearch}>
                  <input
                    type="text"
                    placeholder="Digite o nome da música..."
                    value={artistTrackQuery}
                    onChange={(e) => setArtistTrackQuery(e.target.value)}
                    className="recommender-input"
                  />

                  <button
                    type="submit"
                    className="form-button home-button recommender-search-button"
                    disabled={artistTrackLoading}
                  >
                    {artistTrackLoading ? "Carregando..." : "Filtrar"}
                  </button>
                </form>

                <div className="recommender-results">
                  {artistTrackResults.length > 0 && (
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
                            {selected && <span className="track-selected-badge">Selecionada</span>}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                <div className="recommender-selection">
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
                    className="form-button home-button recommender-confirm-button"
                    onClick={handleConfirmArtistTrackSelection}
                    disabled={!artistSelectedTrack}
                  >
                    Confirmar seleção
                  </button>
                </div>
              </section>
            )}
          </>
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
