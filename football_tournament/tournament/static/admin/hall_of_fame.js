(function () {
    function initHallOfFamePlayerFilter() {
        const teamSelect = document.getElementById("id_team");
        const playerSelect = document.getElementById("id_player");

        if (!teamSelect || !playerSelect) {
            return;
        }

    function getPlayersUrl() {
        const path = window.location.pathname;
        const base = path.replace(/(?:add|\d+\/change)\/$/, "");
        return `${base}player-options/`;
    }

    function setOptions(players, selectedId) {
        while (playerSelect.firstChild) {
            playerSelect.removeChild(playerSelect.firstChild);
        }

        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "---------";
        playerSelect.appendChild(emptyOption);

        players.forEach((player) => {
            const option = document.createElement("option");
            option.value = String(player.id);
            option.textContent = player.label;
            if (selectedId && String(player.id) === String(selectedId)) {
                option.selected = true;
            }
            playerSelect.appendChild(option);
        });
    }

    async function refreshPlayers() {
        const teamId = teamSelect.value;
        const selected = playerSelect.value;

        if (!teamId) {
            setOptions([], null);
            return;
        }

        try {
            const response = await fetch(`${getPlayersUrl()}?team_id=${encodeURIComponent(teamId)}`);
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            setOptions(data.players || [], selected);
        } catch (error) {
            return;
        }
    }

        teamSelect.addEventListener("change", refreshPlayers);

        if (teamSelect.value) {
            refreshPlayers();
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initHallOfFamePlayerFilter);
    } else {
        initHallOfFamePlayerFilter();
    }
})();
