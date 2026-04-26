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
        <label for="playerTeamSearch${index}">Player ${label} Team</label>
        <input id="playerTeamSearch${index}" type="text" placeholder="Type the player's team" autocomplete="off" />
        <label for="playerSearch${index}">Player ${label}</label>
        <input id="playerSearch${index}" type="text" placeholder="Type a player name or numeric ID" autocomplete="off" />
      `;

      container.appendChild(wrapper);

      const teamInput = PrimeScoreApp.getById(`playerTeamSearch${index}`);
      const input = PrimeScoreApp.getById(`playerSearch${index}`);
      teamInput?.addEventListener("input", () => {
        delete input.dataset.playerId;
        delete input.dataset.resolvedName;
      });
      input?.addEventListener("input", () => {
        delete input.dataset.playerId;
        delete input.dataset.resolvedName;
      });
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
      const resolvedTeam = await PrimeScoreApp.apiFetch(`/api/resolve/team?q=${encodeURIComponent(typedValue)}`);
      input.value = resolvedTeam.name || typedValue;
      input.dataset.teamId = String(resolvedTeam.id);
      input.dataset.resolvedName = resolvedTeam.name || typedValue;
      return {
        id: String(resolvedTeam.id),
        name: resolvedTeam.name || typedValue,
      };
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

  async function resolvePlayerInput(teamInput, input, playerLabel) {
    const typedValue = input?.value.trim() || "";
    const typedTeam = teamInput?.value.trim() || "";

    if (!typedValue) {
      throw new Error(`Enter Player ${playerLabel}.`);
    }

    if (input.dataset.playerId && input.dataset.resolvedName === typedValue) {
      return { id: input.dataset.playerId, name: input.dataset.resolvedName };
    }

    if (/^\d+$/.test(typedValue)) {
      const query = new URLSearchParams({ q: typedValue });
      if (typedTeam) {
        query.set("team", typedTeam);
      }

      const resolvedPlayer = await PrimeScoreApp.apiFetch(`/api/resolve/player?${query.toString()}`);
      input.value = resolvedPlayer.name || typedValue;
      input.dataset.playerId = String(resolvedPlayer.id);
      input.dataset.resolvedName = resolvedPlayer.name || typedValue;
      return {
        id: String(resolvedPlayer.id),
        name: resolvedPlayer.name || typedValue,
      };
    }

    if (!typedTeam) {
      throw new Error(`Enter Player ${playerLabel} Team.`);
    }

    const query = new URLSearchParams({
      q: typedValue,
      team: typedTeam,
    });

    const resolvedPlayer = await PrimeScoreApp.apiFetch(`/api/resolve/player?${query.toString()}`);
    input.value = resolvedPlayer.name || typedValue;
    input.dataset.playerId = String(resolvedPlayer.id);
    input.dataset.resolvedName = resolvedPlayer.name || typedValue;

    return {
      id: String(resolvedPlayer.id),
      name: resolvedPlayer.name || typedValue,
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
            const query = new URLSearchParams({ name: team.name });
            if (leagueFilter) {
              query.set("league", leagueFilter);
            }
            return await PrimeScoreApp.apiFetch(
              `/api/teams/${team.id}/statistics?${query.toString()}`
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
    const runId = ++PrimeScoreApp.state.playerCompareRunId;
    const count = Number.parseInt(PrimeScoreApp.getById("playerCompareCount")?.value || "2", 10);
    const resolvedPlayers = [];

    if (resultElement) {
      resultElement.innerHTML = "<p>Loading player comparison...</p>";
    }

    try {
      for (let index = 0; index < count; index += 1) {
        const label = String.fromCharCode(65 + index);
        const teamInput = PrimeScoreApp.getById(`playerTeamSearch${index}`);
        const input = PrimeScoreApp.getById(`playerSearch${index}`);
        const player = await resolvePlayerInput(teamInput, input, label);

        if (resolvedPlayers.some((existingPlayer) => existingPlayer.id === player.id)) {
          throw new Error("Choose different players for comparison.");
        }

        resolvedPlayers.push(player);
      }

      const playerResponses = await Promise.all(
        resolvedPlayers.map((player) => PrimeScoreApp.apiFetch(`/api/players/${player.id}/statistics`))
      );

      if (runId !== PrimeScoreApp.state.playerCompareRunId) {
        return;
      }

      const rows = resolvedPlayers.map((player, index) => ({
        name: playerResponses[index]?.player_name || player.name,
        data: playerResponses[index]?.statistics || {},
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
