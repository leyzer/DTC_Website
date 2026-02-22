-- --------------------------------------------------------
-- Host:                         Z:\Documents$\DTC Website 2026\GPTLeague.db
-- Server version:               3.44.0
-- Server OS:                    
-- HeidiSQL Version:             12.6.0.6765
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES  */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

-- Dumping structure for table GPTLeague.club_memberships
CREATE TABLE IF NOT EXISTS club_memberships (
    membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_member INTEGER DEFAULT 1,
    UNIQUE(season_id, user_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(season_id) REFERENCES seasons(season_id)
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.elo_rules
CREATE TABLE IF NOT EXISTS elo_rules (
    elo_rule_id        INTEGER PRIMARY KEY,
    category           TEXT NOT NULL CHECK (category IN ('AOS','40k','skirmish','mass_battle')),
    points_band        TEXT NOT NULL,           -- 'SP/CP','1000','1500','2000','skirmish','mass_battle'
    base_rating        INTEGER NOT NULL DEFAULT 400,
    k_factor           INTEGER NOT NULL,
    UNIQUE (category, points_band)
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.factions
CREATE TABLE IF NOT EXISTS factions (
    faction_id         INTEGER PRIMARY KEY,
    system_id          INTEGER NOT NULL,
    "faction_name"               TEXT NOT NULL,
    UNIQUE (system_id, "faction_name"),
    FOREIGN KEY (system_id) REFERENCES systems(system_id) ON DELETE CASCADE
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.games
CREATE TABLE IF NOT EXISTS games (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    system_id INTEGER NOT NULL,
    played_on TEXT NOT NULL,
    location_id INTEGER NULL,
    points_band TEXT NOT NULL,
    notes TEXT NULL,
    score INTEGER NULL,
    ignored INTEGER NULL,
    CONSTRAINT fk_location FOREIGN KEY (location_id) REFERENCES locations(location_id) ON UPDATE NO ACTION ON DELETE SET NULL,
    CONSTRAINT fk_system FOREIGN KEY (system_id) REFERENCES systems(system_id) ON UPDATE NO ACTION ON DELETE RESTRICT,
    CONSTRAINT fk_season FOREIGN KEY (season_id) REFERENCES seasons(season_id) ON UPDATE NO ACTION ON DELETE CASCADE
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.game_participants
CREATE TABLE IF NOT EXISTS game_participants (
    game_id            INTEGER NOT NULL,
    player_id          INTEGER NOT NULL,        -- users.user_id
    faction_id         INTEGER,                 -- nullable for systems without factions or unknown
    result             TEXT NOT NULL CHECK (result IN ('win','loss','draw')),
    painting_battle_ready INTEGER NOT NULL DEFAULT 0, -- 0/1
    score_raw          INTEGER,                 -- optional VP or mission score
    PRIMARY KEY (game_id, player_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (faction_id) REFERENCES factions(faction_id) ON DELETE SET NULL
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.locations
CREATE TABLE IF NOT EXISTS locations (
    location_id        INTEGER PRIMARY KEY,
    name               TEXT NOT NULL,           -- e.g., "Top Deck", "Musgrave Hall", "Local GT"
    location_type      TEXT NOT NULL CHECK (location_type IN ('store','other','tournament')),
    city               TEXT,                    -- e.g., "Durban"
    notes              TEXT
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.password_reset_tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
            token_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.ratings
CREATE TABLE IF NOT EXISTS ratings (
    player_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    system_id INTEGER NOT NULL,
    current_rating INTEGER NOT NULL, last_updated TEXT,
    PRIMARY KEY (player_id, season_id, system_id),
    FOREIGN KEY (player_id) REFERENCES users(user_id),
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (system_id) REFERENCES systems(system_id)
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.rating_history
CREATE TABLE IF NOT EXISTS rating_history (
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    system_id INTEGER NOT NULL,
    old_rating INTEGER NOT NULL,
    new_rating INTEGER NOT NULL,
    k_factor_used INTEGER NOT NULL,
    expected_score REAL NOT NULL,
    actual_score REAL NOT NULL,
    PRIMARY KEY (game_id, player_id, system_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES users(user_id),
    FOREIGN KEY (system_id) REFERENCES systems(system_id)
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.seasons
CREATE TABLE IF NOT EXISTS seasons (
    season_id          INTEGER PRIMARY KEY,
    name               TEXT NOT NULL,           -- e.g., "2026 League"
    year               INTEGER NOT NULL,
    start_date         TEXT NOT NULL,           -- ISO date
    end_date           TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'active'  -- 'active', 'archived'
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.systems
CREATE TABLE IF NOT EXISTS systems (
    system_id          INTEGER PRIMARY KEY,
    "system_code"               TEXT NOT NULL UNIQUE,    -- e.g., 'AOS', '40K', 'BB', 'KT', 'TC', 'VW', 'SCABZ', 'SG', 'OLD', 'HH', 'OW', 'HIST'
    "system_name"               TEXT NOT NULL,
    category           TEXT NOT NULL CHECK (category IN ('AOS','40k','skirmish','mass_battle'))
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.system_memberships
CREATE TABLE IF NOT EXISTS system_memberships (
    membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    system_id INTEGER NOT NULL,
    joined_on TEXT DEFAULT (datetime('now')),
    is_active INTEGER DEFAULT 1,
    UNIQUE(user_id, system_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (system_id) REFERENCES systems(system_id)
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.users
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    "user_name"   TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
, "full_name" TEXT NOT NULL, is_provisional INTEGER DEFAULT 0);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.league_settings
CREATE TABLE IF NOT EXISTS league_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(season_id, setting_key),
    FOREIGN KEY(season_id) REFERENCES seasons(season_id)
);

-- Data exporting was unselected.

-- Dumping structure for table GPTLeague.user_roles
CREATE TABLE IF NOT EXISTS user_roles (
    user_id            INTEGER NOT NULL,
    role               TEXT NOT NULL,           -- 'player', 'admin'
    PRIMARY KEY (user_id, role),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
