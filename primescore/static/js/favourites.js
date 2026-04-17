(function (PrimeScoreApp) {
  function normaliseItems(items) {
    return (items || []).map((item) => String(item)).filter(Boolean);
  }

  function renderFavouriteList(items, containerId) {
    const container = PrimeScoreApp.getById(containerId);
    if (!container) {
      return;
    }

    if (!items.length) {
      container.innerHTML = '<p class="message">None saved.</p>';
      return;
    }

    container.innerHTML = `
      <ul class="list">
        ${items.map((item) => `<li>${PrimeScoreApp.escapeHtml(item)}</li>`).join("")}
      </ul>
    `;
  }

  function syncInputsFromState() {
    const { favourite_teams, favourite_players, favourite_leagues } = PrimeScoreApp.state.favourites;

    if (PrimeScoreApp.getById("favTeams")) {
      PrimeScoreApp.getById("favTeams").value = favourite_teams.join(", ");
    }
    if (PrimeScoreApp.getById("favPlayers")) {
      PrimeScoreApp.getById("favPlayers").value = favourite_players.join(", ");
    }
    if (PrimeScoreApp.getById("favLeagues")) {
      PrimeScoreApp.getById("favLeagues").value = favourite_leagues.join(", ");
    }
  }

  function renderFavourites() {
    const { favourite_teams, favourite_players, favourite_leagues } = PrimeScoreApp.state.favourites;

    renderFavouriteList(favourite_teams, "favTeamsList");
    renderFavouriteList(favourite_players, "favPlayersList");
    renderFavouriteList(favourite_leagues, "favLeaguesList");
  }

  async function loadFavourites() {
    try {
      const data = await PrimeScoreApp.apiFetch("/api/favourites");

      PrimeScoreApp.state.favourites = {
        favourite_teams: normaliseItems(data.favourite_teams),
        favourite_players: normaliseItems(data.favourite_players),
        favourite_leagues: normaliseItems(data.favourite_leagues),
      };

      renderFavourites();
      syncInputsFromState();
    } catch (error) {
      PrimeScoreApp.showMessage("favMsg", error.message || "Could not load favourites.");
    }
  }

  async function saveFavourites(event) {
    event?.preventDefault();

    const payload = {
      favourite_teams: PrimeScoreApp.parseCommaList(PrimeScoreApp.getById("favTeams")?.value),
      favourite_players: PrimeScoreApp.parseCommaList(PrimeScoreApp.getById("favPlayers")?.value),
      favourite_leagues: PrimeScoreApp.parseCommaList(PrimeScoreApp.getById("favLeagues")?.value),
    };

    try {
      await PrimeScoreApp.apiFetch("/api/favourites", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      PrimeScoreApp.state.favourites = payload;
      renderFavourites();
      PrimeScoreApp.showMessage("favMsg", "Favourites saved.", false);
      PrimeScoreApp.loadFavouritesSummary?.();
    } catch (error) {
      PrimeScoreApp.showMessage("favMsg", error.message || "Could not save favourites.");
    }
  }

  PrimeScoreApp.loadFavourites = loadFavourites;
  PrimeScoreApp.renderFavourites = renderFavourites;
  PrimeScoreApp.saveFavourites = saveFavourites;
})(window.PrimeScoreApp);
