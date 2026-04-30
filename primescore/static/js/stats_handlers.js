(function (PrimeScoreApp) {
  function showStatsTab(tabId, button) {
    const statsPage = PrimeScoreApp.getById("statsPage");
    if (!statsPage) {
      return;
    }

    statsPage.querySelectorAll(".tab-content").forEach((tab) => {
      tab.classList.remove("active");
      tab.style.display = "none";
    });

    statsPage.querySelectorAll(".tabs .tab-btn").forEach((tabButton) => {
      tabButton.classList.remove("active");
    });

    const activeTab = PrimeScoreApp.getById(tabId);
    if (activeTab) {
      activeTab.classList.add("active");
      activeTab.style.display = "";
    }

    button?.classList.add("active");
  }

  function formatMetricValue(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return Number.isInteger(value) ? String(value) : value.toFixed(1);
    }
    return PrimeScoreApp.escapeHtml(value ?? "");
  }

  function renderMetricGrid(items) {
    return `
      <div class="stat-grid stats-detail-grid">
        ${items
          .map(
            (item) => `
              <div class="card metric-card">
                <strong>${formatMetricValue(item.value)}</strong>
                <span>${PrimeScoreApp.escapeHtml(item.label)}</span>
              </div>
            `
          )
          .join("")}
      </div>
    `;
  }

  function renderTeamStatsCard(teamStats) {
    const advancedMetricsNote =
      teamStats.advanced_stats_matches > 0
        ? `Advanced metrics averaged from the latest ${teamStats.advanced_stats_matches} finished match${teamStats.advanced_stats_matches === 1 ? "" : "es"}.`
        : "Advanced match metrics are currently unavailable for this team.";

    return `
      <div class="card stats-detail-card">
        <div class="stats-detail-header">
          <div>
            <h3>${PrimeScoreApp.escapeHtml(teamStats.team_name || "Team")}</h3>
            <p class="subtitle">${PrimeScoreApp.escapeHtml(advancedMetricsNote)}</p>
          </div>
          ${
            teamStats.team_crest
              ? `<img src="${PrimeScoreApp.escapeHtml(teamStats.team_crest)}" alt="${PrimeScoreApp.escapeHtml(teamStats.team_name || "Team crest")}" class="stats-detail-crest" />`
              : ""
          }
        </div>
        ${renderMetricGrid([
          { label: "Matches", value: teamStats.matches_played ?? 0 },
          { label: "Wins", value: teamStats.wins ?? 0 },
          { label: "Draws", value: teamStats.draws ?? 0 },
          { label: "Losses", value: teamStats.losses ?? 0 },
          { label: "Goals Scored", value: teamStats.goals_scored ?? 0 },
          { label: "Goals Conceded", value: teamStats.goals_conceded ?? 0 },
          { label: "Clean Sheets", value: teamStats.clean_sheets ?? 0 },
          { label: "Avg Possession (%)", value: teamStats.average_possession ?? 0 },
          { label: "Avg Shots", value: teamStats.average_shots ?? 0 },
          { label: "Avg Shots on Target", value: teamStats.average_shots_on_target ?? 0 },
          { label: "Avg Fouls", value: teamStats.average_fouls_committed ?? 0 },
          { label: "Avg Corners", value: teamStats.average_corners ?? 0 },
        ])}
      </div>
    `;
  }

  function renderPlayerStatsCard(playerStats) {
    const playerMetrics = playerStats.statistics || {};
    const teamLine = [playerStats.current_team, playerStats.position].filter(Boolean).join(" - ");

    return `
      <div class="card stats-detail-card">
        <div class="stats-detail-header">
          <div>
            <h3>${PrimeScoreApp.escapeHtml(playerStats.player_name || "Player")}</h3>
            <p class="subtitle">${PrimeScoreApp.escapeHtml(teamLine || "Individual player statistics")}</p>
          </div>
        </div>
        ${renderMetricGrid([
          { label: "Goals", value: playerMetrics.goals ?? 0 },
          { label: "Assists", value: playerMetrics.assists ?? 0 },
          { label: "Appearances", value: playerMetrics.appearances ?? 0 },
          { label: "Minutes", value: playerMetrics.minutes ?? 0 },
          { label: "Rating", value: playerMetrics.rating || "N/A" },
          { label: "Shots", value: playerMetrics.shots ?? 0 },
          { label: "Shots on Target", value: playerMetrics.shots_on_target ?? 0 },
          { label: "Fouls Committed", value: playerMetrics.fouls_committed ?? 0 },
          { label: "Yellow Cards", value: playerMetrics.yellow_cards ?? 0 },
          { label: "Red Cards", value: playerMetrics.red_cards ?? 0 },
        ])}
      </div>
    `;
  }

  async function viewTeamStats() {
    const resultElement = PrimeScoreApp.getById("individualTeamStatsResult");
    const teamInput = PrimeScoreApp.getById("teamStatsSearch");
    const leagueFilter = PrimeScoreApp.getById("statsLeagueFilter")?.value || "";

    if (resultElement) {
      resultElement.innerHTML = "<p>Loading team statistics...</p>";
    }

    try {
      const resolvedTeam = await PrimeScoreApp.resolveTeamInput?.(teamInput, "", leagueFilter);
      const query = new URLSearchParams({ name: resolvedTeam.name });
      if (leagueFilter) {
        query.set("league", leagueFilter);
      }

      const teamStats = await PrimeScoreApp.apiFetch(
        `/api/teams/${resolvedTeam.id}/statistics?${query.toString()}`
      );

      if (resultElement) {
        resultElement.innerHTML = renderTeamStatsCard(teamStats);
      }
    } catch (error) {
      if (resultElement) {
        resultElement.innerHTML = `<p class="error">${PrimeScoreApp.escapeHtml(error.message || "Team statistics could not be loaded.")}</p>`;
      }
    }
  }

  async function viewPlayerStats() {
    const resultElement = PrimeScoreApp.getById("individualPlayerStatsResult");
    const teamInput = PrimeScoreApp.getById("playerStatsTeamSearch");
    const playerInput = PrimeScoreApp.getById("playerStatsSearch");

    if (resultElement) {
      resultElement.innerHTML = "<p>Loading player statistics...</p>";
    }

    try {
      const resolvedPlayer = await PrimeScoreApp.resolvePlayerInput?.(teamInput, playerInput, "");
      const playerStats = await PrimeScoreApp.apiFetch(`/api/players/${resolvedPlayer.id}/statistics`);

      if (resultElement) {
        resultElement.innerHTML = renderPlayerStatsCard(playerStats);
      }
    } catch (error) {
      if (resultElement) {
        resultElement.innerHTML = `<p class="error">${PrimeScoreApp.escapeHtml(error.message || "Player statistics could not be loaded.")}</p>`;
      }
    }
  }

  function initialiseStatsPage() {
    const teamInput = PrimeScoreApp.getById("teamStatsSearch");
    const leagueFilter = PrimeScoreApp.getById("statsLeagueFilter");
    const playerTeamInput = PrimeScoreApp.getById("playerStatsTeamSearch");
    const playerInput = PrimeScoreApp.getById("playerStatsSearch");

    leagueFilter?.addEventListener("change", () => {
      if (teamInput) {
        delete teamInput.dataset.teamId;
        delete teamInput.dataset.resolvedName;
      }
    });

    playerTeamInput?.addEventListener("input", () => {
      if (playerInput) {
        delete playerInput.dataset.playerId;
        delete playerInput.dataset.resolvedName;
      }
    });

    playerInput?.addEventListener("input", () => {
      delete playerInput.dataset.playerId;
      delete playerInput.dataset.resolvedName;
    });
  }

  PrimeScoreApp.initialiseStatsPage = initialiseStatsPage;
  PrimeScoreApp.loadStatsPage = () => {};
  PrimeScoreApp.showStatsTab = showStatsTab;
  PrimeScoreApp.viewTeamStats = viewTeamStats;
  PrimeScoreApp.viewPlayerStats = viewPlayerStats;
})(window.PrimeScoreApp);
