(function (PrimeScoreApp) {
  function normaliseItems(items) {
    return (items || []).map((item) => String(item)).filter(Boolean);
  }

  function applyFavouriteState(
    data,
    { preferNewestHomeLeague = false, selectedLeague = null } = {},
  ) {
    const favouriteTeams = normaliseItems(data.favourite_teams);
    const favouritePlayers = normaliseItems(data.favourite_players);
    const favouriteLeagues = normaliseItems(data.favourite_leagues);
    const favouriteTeamIds = normaliseItems(data.favourite_team_ids);
    const favouritePlayerIds = normaliseItems(data.favourite_player_ids);
    const favouriteLeagueCodes = normaliseItems(data.favourite_league_codes);

    PrimeScoreApp.state.favourites = {
      favourite_teams: favouriteTeams,
      favourite_players: favouritePlayers,
      favourite_leagues: favouriteLeagues,
      favourite_team_ids: favouriteTeamIds,
      favourite_player_ids: favouritePlayerIds,
      favourite_league_codes: favouriteLeagueCodes,
    };

    PrimeScoreApp.state.favouriteLeagueOptions = favouriteLeagues.map(
      (name, index) => ({
        name,
        code: favouriteLeagueCodes[index] || name,
      }),
    );

    if (selectedLeague?.code) {
      PrimeScoreApp.state.homeLeagueCode = String(selectedLeague.code);
      PrimeScoreApp.state.homeLeagueName = selectedLeague.name || "";
    }

    const newestLeague = PrimeScoreApp.state.favouriteLeagueOptions.at(-1);
    const currentLeagueStillSaved =
      PrimeScoreApp.state.favouriteLeagueOptions.some(
        (league) => league.code === PrimeScoreApp.state.homeLeagueCode,
      );

    if (preferNewestHomeLeague && newestLeague) {
      PrimeScoreApp.state.homeLeagueCode = newestLeague.code;
      PrimeScoreApp.state.homeLeagueName = newestLeague.name;
    } else if (
      !PrimeScoreApp.state.homeLeagueCode ||
      !currentLeagueStillSaved
    ) {
      PrimeScoreApp.state.homeLeagueCode =
        newestLeague?.code || PrimeScoreApp.state.homeLeagueCode || "";
      PrimeScoreApp.state.homeLeagueName =
        newestLeague?.name || PrimeScoreApp.state.homeLeagueName || "";
    }
  }

  function renderMatchCards(matches, containerId, emptyText) {
    const container = PrimeScoreApp.getById(containerId);
    if (!container) {
      return;
    }

    if (!matches.length) {
      container.innerHTML = `<p class="empty">${emptyText}</p>`;
      return;
    }

    container.innerHTML = matches
      .map(
        (match) => `
          <div class="match-card">
            <div class="teams">${PrimeScoreApp.escapeHtml(match.home_team)} vs ${PrimeScoreApp.escapeHtml(match.away_team)}</div>
            <div class="score">${match.home_score ?? "-"} : ${match.away_score ?? "-"}</div>
            <div class="meta">${PrimeScoreApp.escapeHtml(match.competition || "")} - ${new Date(
              match.date || match.match_date || "",
            ).toLocaleString()}</div>
            ${match.status ? `<div class="status">${PrimeScoreApp.escapeHtml(match.status)}</div>` : ""}
          </div>
        `,
      )
      .join("");
  }

  function renderLeagueTables(tables, containerId) {
    const container = PrimeScoreApp.getById(containerId);
    if (!container) {
      return;
    }

    if (!tables.length) {
      container.innerHTML = '<p class="empty">No standings available.</p>';
      return;
    }

    const table = tables[0];
    const rows = (table.standings || [])
      .map(
        (row) => `
          <tr>
            <td>${row.position}</td>
            <td><img src="${row.team_crest || ""}" class="crest" alt="" />${PrimeScoreApp.escapeHtml(row.team)}</td>
            <td>${row.played}</td>
            <td>${row.won}</td>
            <td>${row.drawn}</td>
            <td>${row.lost}</td>
            <td>${row.goals_for}</td>
            <td>${row.goals_against}</td>
            <td>${row.goal_difference}</td>
            <td>${row.points}</td>
          </tr>
        `,
      )
      .join("");

    container.innerHTML = `
      <div class="table-card">
        <h4>${PrimeScoreApp.escapeHtml(table.competition)} (${PrimeScoreApp.escapeHtml(table.season)})</h4>
        <table class="standings">
          <thead>
            <tr>
              <th>#</th><th>Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function renderFavouritePlayerCards(playerStats) {
    const section = PrimeScoreApp.getById("favouritePlayersSection");
    const container = PrimeScoreApp.getById("favouritePlayersHome");
    const hasSavedPlayers =
      (PrimeScoreApp.state.favourites.favourite_players || []).length > 0;

    if (!section || !container) {
      return;
    }

    if (!hasSavedPlayers) {
      PrimeScoreApp.hideElement(section);
      container.innerHTML = "";
      return;
    }

    PrimeScoreApp.showElement(section, "block");

    if (!playerStats.length) {
      container.innerHTML =
        '<p class="empty">No favourite player stats available right now.</p>';
      return;
    }

    container.innerHTML = playerStats
      .map(
        (player) => `
          <article class="card player-stat-card">
            <div class="section-header">
              <div>
                <h4>${PrimeScoreApp.escapeHtml(player.player_name || "Player")}</h4>
                <p class="subtitle">${PrimeScoreApp.escapeHtml(player.current_team || "Unknown team")} ${player.position ? `- ${PrimeScoreApp.escapeHtml(player.position)}` : ""}</p>
              </div>
              ${player.photo ? `<img src="${PrimeScoreApp.escapeHtml(player.photo)}" class="crest player-photo" alt="${PrimeScoreApp.escapeHtml(player.player_name || "Player")}" />` : ""}
            </div>
            <div class="stat-grid">
              <div><strong>${player.statistics?.goals ?? 0}</strong><span>Goals</span></div>
              <div><strong>${player.statistics?.assists ?? 0}</strong><span>Assists</span></div>
              <div><strong>${player.statistics?.appearances ?? 0}</strong><span>Apps</span></div>
              <div><strong>${player.statistics?.minutes ?? 0}</strong><span>Minutes</span></div>
              <div><strong>${player.statistics?.yellow_cards ?? 0}</strong><span>Yellows</span></div>
              <div><strong>${player.statistics?.red_cards ?? 0}</strong><span>Reds</span></div>
            </div>
            ${player.statistics?.rating ? `<p class="subtitle">Rating: ${PrimeScoreApp.escapeHtml(player.statistics.rating)}</p>` : ""}
          </article>
        `,
      )
      .join("");
  }

  function renderHomeLeagueSwitcher(selectedLeague = null) {
    const leagueName = PrimeScoreApp.getById("homeLeagueName");
    const leaguePosition = PrimeScoreApp.getById("homeLeaguePosition");
    const previousButton = PrimeScoreApp.getById("homeLeaguePrev");
    const nextButton = PrimeScoreApp.getById("homeLeagueNext");
    const favouriteLeagues = PrimeScoreApp.state.favouriteLeagueOptions || [];

    const effectiveLeagueName =
      selectedLeague?.name ||
      PrimeScoreApp.state.homeLeagueName ||
      favouriteLeagues.find(
        (league) => league.code === PrimeScoreApp.state.homeLeagueCode,
      )?.name ||
      "Premier League";

    if (leagueName) {
      leagueName.textContent = effectiveLeagueName;
    }

    const currentIndex = favouriteLeagues.findIndex(
      (league) => league.code === PrimeScoreApp.state.homeLeagueCode,
    );
    const hasMultipleLeagues = favouriteLeagues.length > 1;

    if (leaguePosition) {
      if (!favouriteLeagues.length) {
        leaguePosition.textContent = "Default league";
      } else if (currentIndex >= 0) {
        leaguePosition.textContent = `League ${currentIndex + 1} of ${favouriteLeagues.length}`;
      } else {
        leaguePosition.textContent = "Favourite league";
      }
    }

    if (previousButton) {
      previousButton.disabled = !hasMultipleLeagues;
    }

    if (nextButton) {
      nextButton.disabled = !hasMultipleLeagues;
    }
  }

  async function loadFavouritesSummary(options = {}) {
    try {
      const data = await PrimeScoreApp.apiFetch("/api/favourites");
      applyFavouriteState(data, options);

      PrimeScoreApp.getById("teamsCount")?.replaceChildren(
        document.createTextNode(
          String(PrimeScoreApp.state.favourites.favourite_teams.length),
        ),
      );
      PrimeScoreApp.getById("playersCount")?.replaceChildren(
        document.createTextNode(
          String(PrimeScoreApp.state.favourites.favourite_players.length),
        ),
      );
      PrimeScoreApp.getById("leaguesCount")?.replaceChildren(
        document.createTextNode(
          String(PrimeScoreApp.state.favourites.favourite_leagues.length),
        ),
      );

      PrimeScoreApp.showSummaryTab?.("teams");
      renderHomeLeagueSwitcher(options.selectedLeague);
    } catch (error) {
      console.error("[loadFavouritesSummary]", error);
    }
  }

  function showSummaryTab(which, event) {
    event?.preventDefault?.();

    document.querySelectorAll(".summary-tab").forEach((button) => {
      button.classList.toggle(
        "active",
        button.textContent.toLowerCase().includes(which),
      );
    });

    const key =
      which === "players"
        ? "favourite_players"
        : which === "leagues"
          ? "favourite_leagues"
          : "favourite_teams";
    const items = PrimeScoreApp.state.favourites[key] || [];
    const content = PrimeScoreApp.getById("summaryContent");

    if (!content) {
      return;
    }

    if (!items.length) {
      content.innerHTML = '<p class="message">No favourites yet.</p>';
      return;
    }

    content.innerHTML = `
      <ul class="list">
        ${items
          .map(
            (item) =>
              `<li><span>${PrimeScoreApp.escapeHtml(item.name || item)}</span></li>`,
          )
          .join("")}
      </ul>
    `;
  }

  async function loadHome(forceReload = false, preferredLeagueCode = null) {
    if (!forceReload && PrimeScoreApp.state.homeRequestPromise) {
      return PrimeScoreApp.state.homeRequestPromise;
    }

    PrimeScoreApp.state.homeRequestPromise = (async () => {
      try {
        const leagueCode =
          preferredLeagueCode || PrimeScoreApp.state.homeLeagueCode || "";
        const url = leagueCode
          ? `/api/home-screen?league=${encodeURIComponent(leagueCode)}`
          : "/api/home-screen";
        const data = await PrimeScoreApp.apiFetch(url);

        if (data.selected_league?.code) {
          PrimeScoreApp.state.homeLeagueCode = String(
            data.selected_league.code,
          );
          PrimeScoreApp.state.homeLeagueName = data.selected_league.name || "";
        }

        renderMatchCards(
          data.live_matches || [],
          "liveMatchesHome",
          "No live matches right now.",
        );
        renderMatchCards(
          data.upcoming_fixtures || [],
          "upcomingFixturesHome",
          "No upcoming fixtures.",
        );
        renderMatchCards(
          data.recent_results || [],
          "recentResultsHome",
          "No recent results.",
        );
        renderLeagueTables(data.league_tables || [], "leagueTablesHome");
        await loadFavouritesSummary({ selectedLeague: data.selected_league });
        renderFavouritePlayerCards(data.favourite_player_stats || []);
      } catch (error) {
        console.error("[loadHome]", error);
      } finally {
        PrimeScoreApp.state.homeRequestPromise = null;
      }
    })();

    return PrimeScoreApp.state.homeRequestPromise;
  }

  async function cycleHomeLeague(direction) {
    const favouriteLeagues = PrimeScoreApp.state.favouriteLeagueOptions || [];
    if (favouriteLeagues.length < 2) {
      return;
    }

    const currentIndex = favouriteLeagues.findIndex(
      (league) => league.code === PrimeScoreApp.state.homeLeagueCode,
    );
    const safeIndex =
      currentIndex >= 0 ? currentIndex : favouriteLeagues.length - 1;
    const nextIndex =
      (safeIndex + direction + favouriteLeagues.length) %
      favouriteLeagues.length;
    const nextLeague = favouriteLeagues[nextIndex];

    PrimeScoreApp.state.homeLeagueCode = nextLeague.code;
    PrimeScoreApp.state.homeLeagueName = nextLeague.name;
    renderHomeLeagueSwitcher(nextLeague);
    await loadHome(true, nextLeague.code);
  }

  PrimeScoreApp.showSummaryTab = showSummaryTab;
  PrimeScoreApp.loadHome = loadHome;
  PrimeScoreApp.renderMatchCards = renderMatchCards;
  PrimeScoreApp.renderLeagueTables = renderLeagueTables;
  PrimeScoreApp.renderFavouritePlayerCards = renderFavouritePlayerCards;
  PrimeScoreApp.loadFavouritesSummary = loadFavouritesSummary;
  PrimeScoreApp.cycleHomeLeague = cycleHomeLeague;
})(window.PrimeScoreApp);
