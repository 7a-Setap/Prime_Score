(function (PrimeScoreApp) {
  function buildTeamInputs() {
    const container = PrimeScoreApp.getById("teamCompareInputs");
    const count = Number.parseInt(PrimeScoreApp.getById("teamCompareCount")?.value || "2", 10);

    if (!container) {
      return;
    }

    container.innerHTML = "";

    for (let index = 0; index < count; index += 1) {
      const label = String.fromCharCode(65 + index);
      const wrapper = document.createElement("div");

      wrapper.className = "compare-input-group";
      wrapper.innerHTML = `
        <label for="teamSearch${index}">Team ${label}</label>
        <input id="teamSearch${index}" type="text" placeholder="Type a team name or numeric ID" autocomplete="off" />
      `;

      container.appendChild(wrapper);

      const input = PrimeScoreApp.getById(`teamSearch${index}`);
      input?.addEventListener("input", () => {
        delete input.dataset.teamId;
        delete input.dataset.resolvedName;
      });
    }
  }

  function updatePlayerCompareInputs() {
    const container = PrimeScoreApp.getById("playerCompareInputs");
    const count = Number.parseInt(PrimeScoreApp.getById("playerCompareCount")?.value || "2", 10);

    if (!container) {
      return;
    }

    container.innerHTML = "";

    for (let index = 0; index < count; index += 1) {
      const label = String.fromCharCode(65 + index);
      const wrapper = document.createElement("div");

      wrapper.className = "compare-input-group";
      wrapper.innerHTML = `
        <label for="playerSearch${index}">Player ${label}</label>
        <input id="playerSearch${index}" type="text" placeholder="Enter player numeric ID" autocomplete="off" />
      `;

      container.appendChild(wrapper);
    }
  }

  async function resolveTeamInput(input, teamLabel, leagueFilter) {
    const typedValue = input?.value.trim() || "";

    if (!typedValue) {
      throw new Error(`Enter Team ${teamLabel}.`);
    }

    if (input.dataset.teamId && input.dataset.resolvedName === typedValue) {
      return { id: input.dataset.teamId, name: input.dataset.resolvedName };
    }

    if (/^\d+$/.test(typedValue)) {
      input.dataset.teamId = typedValue;
      input.dataset.resolvedName = typedValue;
      return { id: typedValue, name: typedValue };
    }

    const query = new URLSearchParams({ q: typedValue });
    if (leagueFilter) {
      query.set("league", leagueFilter);
    }

    const resolvedTeam = await PrimeScoreApp.apiFetch(`/api/resolve/team?${query.toString()}`);

    input.value = resolvedTeam.name || typedValue;
    input.dataset.teamId = String(resolvedTeam.id);
    input.dataset.resolvedName = resolvedTeam.name || typedValue;

    return {
      id: String(resolvedTeam.id),
      name: resolvedTeam.name || typedValue,
    };
  }

  function getStandingsFallback(standings, team) {
    const matchingRow = (standings || []).find(
      (row) =>
        String(row.team_id || "") === String(team.id) ||
        String(row.team || "").toLowerCase() === String(team.name || "").toLowerCase()
    );

    if (!matchingRow) {
      return null;
    }

    return {
      team_id: team.id,
      team_name: matchingRow.team || team.name,
      team_crest: matchingRow.team_crest || "",
      matches_played: matchingRow.played || 0,
      wins: matchingRow.won || 0,
      draws: matchingRow.drawn || 0,
      losses: matchingRow.lost || 0,
      goals_scored: matchingRow.goals_for || 0,
      goals_conceded: matchingRow.goals_against || 0,
      clean_sheets: 0,
    };
  }

  function renderComparisonTable(rows, labels, valueSelector) {
    if (!rows.length) {
      return '<p class="empty">No comparison data found.</p>';
    }

    let html = '<table class="comparison-table"><thead><tr><th>Stat</th>';
    rows.forEach((row) => {
      html += `<th>${PrimeScoreApp.escapeHtml(row.name)}</th>`;
    });
    html += "</tr></thead><tbody>";

    labels.forEach(({ key, label }) => {
      const values = rows.map((row) => valueSelector(row.data, key));
      const highestValue = Math.max(...values);

      html += `<tr><td>${label}</td>`;
      values.forEach((value) => {
        const highlight = highestValue > 0 && value === highestValue ? ' class="highlight"' : "";
        html += `<td${highlight}>${value}</td>`;
      });
      html += "</tr>";
    });

    html += "</tbody></table>";
    return html;
  }

  async function compareTeamsMultiple() {
    const resultElement = PrimeScoreApp.getById("teamComparisonResult");
    const runId = ++PrimeScoreApp.state.teamCompareRunId;
    const teamCount = Number.parseInt(PrimeScoreApp.getById("teamCompareCount")?.value || "2", 10);
    const leagueFilter = PrimeScoreApp.getById("teamLeagueFilter")?.value || "";
    const resolvedTeams = [];

    if (resultElement) {
      resultElement.innerHTML = "<p>Loading team comparison...</p>";
    }

    try {
      for (let index = 0; index < teamCount; index += 1) {
        const label = String.fromCharCode(65 + index);
        const input = PrimeScoreApp.getById(`teamSearch${index}`);
        const team = await resolveTeamInput(input, label, leagueFilter);

        if (resolvedTeams.some((existingTeam) => existingTeam.id === team.id)) {
          throw new Error("Choose different teams for comparison.");
        }

        resolvedTeams.push(team);
      }

      const standings = leagueFilter ? await PrimeScoreApp.fetchStandings(leagueFilter) : [];
      const teamStats = await Promise.all(
        resolvedTeams.map(async (team) => {
          try {
            return await PrimeScoreApp.apiFetch(
              `/api/teams/${team.id}/statistics?name=${encodeURIComponent(team.name)}`
            );
          } catch (error) {
            return getStandingsFallback(standings, team);
          }
        })
      );

      if (runId !== PrimeScoreApp.state.teamCompareRunId) {
        return;
      }

      const rows = resolvedTeams.map((team, index) => ({
        name: teamStats[index]?.team_name || team.name,
        data: teamStats[index] || getStandingsFallback(standings, team) || {},
      }));

      if (resultElement) {
        resultElement.innerHTML = renderComparisonTable(
          rows,
          [
            { key: "matches_played", label: "Matches" },
            { key: "wins", label: "Wins" },
            { key: "draws", label: "Draws" },
            { key: "losses", label: "Losses" },
            { key: "goals_scored", label: "Goals For" },
            { key: "goals_conceded", label: "Goals Against" },
            { key: "clean_sheets", label: "Clean Sheets" },
          ],
          (data, key) => data[key] ?? 0
        );
      }
    } catch (error) {
      if (resultElement) {
        resultElement.innerHTML = `<p class="error">${PrimeScoreApp.escapeHtml(error.message || "Team comparison failed.")}</p>`;
      }
    }
  }

  async function comparePlayersMultiple() {
    const resultElement = PrimeScoreApp.getById("playerComparisonResult");
    const count = Number.parseInt(PrimeScoreApp.getById("playerCompareCount")?.value || "2", 10);
    const playerIds = [];

    for (let index = 0; index < count; index += 1) {
      const label = String.fromCharCode(65 + index);
      const playerId = PrimeScoreApp.getById(`playerSearch${index}`)?.value.trim() || "";

      if (!/^\d+$/.test(playerId)) {
        if (resultElement) {
          resultElement.innerHTML = `<p class="error">Enter a numeric ID for Player ${label}.</p>`;
        }
        return;
      }

      if (playerIds.includes(playerId)) {
        if (resultElement) {
          resultElement.innerHTML = '<p class="error">Choose different players for comparison.</p>';
        }
        return;
      }

      playerIds.push(playerId);
    }

    if (resultElement) {
      resultElement.innerHTML = "<p>Loading player comparison...</p>";
    }

    try {
      const playerResponses = await Promise.all(
        playerIds.map((playerId) => PrimeScoreApp.apiFetch(`/api/players/${playerId}/statistics`))
      );

      const rows = playerResponses.map((player) => ({
        name: player.player_name || `Player ${player.player_id}`,
        data: player.statistics || {},
      }));

      if (resultElement) {
        resultElement.innerHTML = renderComparisonTable(
          rows,
          [
            { key: "goals", label: "Goals" },
            { key: "assists", label: "Assists" },
            { key: "appearances", label: "Appearances" },
            { key: "yellow_cards", label: "Yellow Cards" },
            { key: "red_cards", label: "Red Cards" },
          ],
          (data, key) => data[key] ?? 0
        );
      }
    } catch (error) {
      if (resultElement) {
        resultElement.innerHTML = `<p class="error">${PrimeScoreApp.escapeHtml(error.message || "Player comparison failed.")}</p>`;
      }
    }
  }

  PrimeScoreApp.buildTeamInputs = buildTeamInputs;
  PrimeScoreApp.compareTeamsMultiple = compareTeamsMultiple;
  PrimeScoreApp.updatePlayerCompareInputs = updatePlayerCompareInputs;
  PrimeScoreApp.comparePlayersMultiple = comparePlayersMultiple;
})(window.PrimeScoreApp);
