(function (PrimeScoreApp) {
  async function loadLeagueFromQuery() {
    const query = PrimeScoreApp.getById("leagueSearch")?.value.trim() || "";

    PrimeScoreApp.clearMessage("leagueError");

    if (!query) {
      PrimeScoreApp.loadDefaultLeagues?.();
      return;
    }

    if (query.length < 3) {
      return;
    }

    try {
      const league = await PrimeScoreApp.apiFetch(`/api/resolve/league?q=${encodeURIComponent(query)}`);
      await PrimeScoreApp.loadStanding?.(String(league.id || query));
    } catch (error) {
      const standingsContainer = PrimeScoreApp.getById("leagueStandingsDisplay");
      if (standingsContainer) {
        standingsContainer.innerHTML = "";
      }
      PrimeScoreApp.showMessage("leagueError", error.message || "League not found.");
    }
  }

  const searchLeagues = PrimeScoreApp.debounce(loadLeagueFromQuery, 300);

  PrimeScoreApp.searchLeagues = searchLeagues;
})(window.PrimeScoreApp);
