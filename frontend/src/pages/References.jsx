import { useNavigate } from "react-router-dom";
import {
  FaGithub,
  FaEnvelope,
  FaExternalLinkAlt,
  FaUniversity,
  FaUserGraduate,
  FaUserTie,
  FaBook,
} from "react-icons/fa";
import "../styles/Home.css";
import "../styles/Recommender.css";
import "../styles/References.css";

import profilePhoto from "../assets/references/profile.png";
import uspEachPhoto from "../assets/references/each-usp.png";

export default function References() {
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

      <main className="form-container recommender-container references-container">
        <section className="references-hero">
          <div className="references-profile-card">
            <img
              src={profilePhoto}
              alt="João Víctor Ferreira Araujo"
              className="references-profile-image"
            />
            <div className="references-profile-content">
              <span className="references-badge">Projeto acadêmico</span>
              <h1 className="references-title">Referências e apresentação</h1>
              <p className="references-description">
                Esta seção apresenta o contexto acadêmico da pesquisa em
                desenvolvimento, informações sobre o autor, orientação, vínculo
                institucional e canais de contato para dúvidas, sugestões ou
                interesse acadêmico no trabalho.
              </p>
            </div>
          </div>
        </section>

        <section className="references-grid">
          <article className="references-card">
            <div className="references-card-header">
              <FaBook className="references-card-icon" />
              <h2>Sobre a pesquisa</h2>
            </div>

            <p>
              A grande variedade de produtos e serviços digitais atualmente
              disponíveis gera uma necessidade constante de organização e
              redirecionamento de itens adequados para cada perfil de usuário
              final. Nesse contexto, sistemas de recomendação têm papel
              relevante ao personalizar a experiência de uso e apoiar a
              apresentação de conteúdos de interesse ao usuário.
            </p>

            <p>
              Em muitos cenários, essas recomendações são produzidas a partir de
              informações relacionadas ao histórico de atividades dos
              indivíduos. Entretanto, há situações em que pouco ou nada se sabe
              sobre esse histórico. Esse é o caso do problema de{" "}
              <strong>cold-start</strong>, em que a informação disponível pode
              ser extremamente limitada, como ocorre com um usuário novo em um
              sistema de recomendação.
            </p>

            <p>
              No contexto da recomendação musical, esta pesquisa tem como
              objetivo investigar uma proposta de solução para o problema de
              cold-start a partir da utilização de apenas uma única informação
              fornecida pelo usuário final: uma música escolhida como preferida.
              A partir dessa informação pontual, busca-se viabilizar
              recomendações musicais coerentes, mesmo em cenários com escassez
              de dados sobre o usuário.
            </p>

            <p>
              Este trabalho está sendo desenvolvido no âmbito do meu mestrado,
              com defesa prevista para <strong>agosto de 2026</strong>. Como a
              dissertação ainda não terá sido concluída nesta etapa, o texto
              final, a denominação oficial do trabalho e eventuais resultados
              consolidados ainda poderão sofrer ajustes.
            </p>

            <p>
              Todas as músicas utilizadas pelo sistema foram coletadas a partir
              de bases de dados públicas disponíveis na internet. Nenhum dado
              utilizado no sistema será persistido ou reutilizado após o
              encerramento do projeto acadêmico.
            </p>
          </article>

          <article className="references-card">
            <div className="references-card-header">
              <FaUserGraduate className="references-card-icon" />
              <h2>Sobre o autor</h2>
            </div>

            <p>
              Meu nome é <strong>João Víctor Ferreira Araujo</strong>. Sou
              pesquisador e estudante da <strong>Universidade de São Paulo</strong>,
              no campus <strong> EACH-USP</strong>, e desenvolvo esta pesquisa
              na área de sistemas de recomendação, com foco em recomendação
              musical, análise de conteúdo e abordagens para o problema de
              cold-start.
            </p>

            <p>
              Caso você tenha interesse no trabalho, queira discutir aspectos
              técnicos, metodológicos ou acadêmicos da pesquisa, fico à
              disposição para contato. Como o trabalho final ainda está em
              desenvolvimento, informações adicionais poderão ser fornecidas
              diretamente mediante contato.
            </p>

            <div className="references-links">
              <a
                href="https://github.com/joao-fa/ContentBased-Music-First-Recommendation"
                target="_blank"
                rel="noopener noreferrer"
                className="references-link-button"
              >
                <FaGithub />
                GitHub do repositório
                <FaExternalLinkAlt className="references-link-external" />
              </a>

              <a
                href="https://github.com/joao-fa"
                target="_blank"
                rel="noopener noreferrer"
                className="references-link-button"
              >
                <FaGithub />
                Meu GitHub
                <FaExternalLinkAlt className="references-link-external" />
              </a>

              <a
                href="mailto:joaovicttor_a@usp.br"
                className="references-link-button"
              >
                <FaEnvelope />
                E-mail de contato
              </a>

              <a
                href="http://lattes.cnpq.br/8105320948007979"
                target="_blank"
                rel="noopener noreferrer"
                className="references-link-button"
              >
                <FaExternalLinkAlt />
                Currículo Lattes
                <FaExternalLinkAlt className="references-link-external" />
              </a>
            </div>
          </article>

          <article className="references-card">
            <div className="references-card-header">
              <FaUserTie className="references-card-icon" />
              <h2>Orientação acadêmica</h2>
            </div>

            <div className="references-contact-block">
              <h3>Orientadora</h3>
              <p><strong>MARISLEI NISHIJIMA</strong></p>
              <a href="mailto:marislei@usp.br">
                marislei@usp.br
              </a>
            </div>

            <div className="references-contact-block">
              <h3>Coorientador</h3>
              <p><strong>LUCIANO DIGIAMPIETRI</strong></p>
              <a href="mailto:digiampietri@usp.br">
                digiampietri@usp.br
              </a>
            </div>

            <p className="references-note">
              Os nomes e e-mails acima podem ser atualizados com os dados
              oficiais antes da publicação final.
            </p>
          </article>

          <article className="references-card">
            <div className="references-card-header">
              <FaUniversity className="references-card-icon" />
              <h2>Vínculo institucional</h2>
            </div>

            <img
              src={uspEachPhoto}
              alt="Universidade de São Paulo - EACH"
              className="references-institution-image"
            />

            <p>
              Universidade de São Paulo (USP) <br />
              Escola de Artes, Ciências e Humanidades (EACH) <br />
              São Paulo, Brasil
            </p>
          </article>

          <article className="references-card references-card-full">
            <div className="references-card-header">
              <FaBook className="references-card-icon" />
              <h2>Observações importantes</h2>
            </div>

            <ul className="references-list">
              <li>
                Esta aplicação possui finalidade acadêmica e experimental.
              </li>
              <li>
                O trabalho ainda está em desenvolvimento e poderá passar por
                ajustes metodológicos, técnicos, textuais e visuais até sua
                versão final.
              </li>
              <li>
                A dissertação correspondente ainda não foi entregue, de modo que
                o título oficial do trabalho e a redação definitiva ainda podem
                sofrer alterações.
              </li>
              <li>
                Resultados finais, documentação consolidada e materiais
                completos poderão ser disponibilizados após a conclusão e defesa
                do trabalho.
              </li>
              <li>
                Em caso de dúvidas, interesse acadêmico ou solicitação de
                informações adicionais, entre em contato pelos canais listados
                nesta página.
              </li>
            </ul>
          </article>
        </section>
      </main>

      <footer className="home-footer">
        <div className="footer-content">
          <p className="footer-text">
            Projeto acadêmico desenvolvido para pesquisa em sistemas de
            recomendação musical baseados em conteúdo. Consulte esta página para
            mais informações institucionais e de contato.
          </p>
          <p className="footer-info">
            © {new Date().getFullYear()} João Víctor Ferreira Araujo —
            Universidade de São Paulo (EACH-USP)
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