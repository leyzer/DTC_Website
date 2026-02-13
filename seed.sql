-- ===========================
-- Systems
-- ===========================
INSERT INTO systems (system_id, system_code, system_name, category) VALUES
  (1, 'AOS', 'Age of Sigmar', 'AOS'),
  (2, '40K', 'Warhammer 40,000', '40k'),
  (3, 'BB', 'Blood Bowl', 'skirmish'),
  (4, 'KT', 'Kill Team', 'skirmish'),
  (5, 'TC', 'Titanicus/Commander', 'skirmish'),
  (6, 'VW', 'Verrotwood', 'skirmish'),
  (7, 'SCABZ', 'Scabz', 'skirmish'),
  (8, 'SG', 'Stargrave', 'skirmish'),
  (9, 'OLD', 'Old Hammer', 'mass_battle'),
  (10, 'HH', 'Horus Heresy', 'mass_battle'),
  (11, 'OW', 'Oathmark/Old World', 'mass_battle'),
  (12, 'HIST', 'Historical', 'mass_battle');

-- ===========================
-- Seasons
-- ===========================
INSERT INTO seasons (season_id, name, year, start_date, end_date, status) VALUES
  (2010, 'Season 2010', 2010, '2010-02-01 00:00:00', '2010-12-31 23:59:59', 'canceled'),
  (2011, 'Season 2011', 2011, '2011-02-01 00:00:00', '2011-12-31 23:59:59', 'canceled'),
  (2012, 'Season 2012', 2012, '2012-02-01 00:00:00', '2012-12-31 23:59:59', 'canceled'),
  (2013, 'Season 2013', 2013, '2013-02-01 00:00:00', '2013-12-31 23:59:59', 'canceled'),
  (2014, 'Season 2014', 2014, '2014-02-01 00:00:00', '2014-12-31 23:59:59', 'canceled'),
  (2015, 'Season 2015', 2015, '2015-02-01 00:00:00', '2015-12-31 23:59:59', 'canceled'),
  (2016, 'Season 2016', 2016, '2016-02-01 00:00:00', '2016-12-31 23:59:59', 'canceled'),
  (2017, 'Season 2017', 2017, '2017-02-01 00:00:00', '2017-12-31 23:59:59', 'canceled'),
  (2018, 'Season 2018', 2018, '2018-02-01 00:00:00', '2018-12-31 23:59:59', 'canceled'),
  (2019, 'Season 2019', 2019, '2019-02-01 00:00:00', '2019-12-31 23:59:59', 'canceled'),
  (2020, 'Season 2020', 2020, '2020-02-01 00:00:00', '2020-12-31 23:59:59', 'canceled'),
  (2021, 'Season 2021', 2021, '2021-02-01 00:00:00', '2021-12-31 23:59:59', 'canceled'),
  (2022, 'Season 2022', 2022, '2022-02-01 00:00:00', '2022-12-31 23:59:59', 'canceled'),
  (2023, 'Season 2023', 2023, '2023-02-01 00:00:00', '2023-12-31 23:59:59', 'canceled'),
  (2024, 'Season 2024', 2024, '2024-02-01 00:00:00', '2024-12-31 23:59:59', 'archived'),
  (2025, 'Season 2025', 2025, '2025-02-01 00:00:00', '2025-12-31 23:59:59', 'archived'),
  (2026, 'Season 2026', 2026, '2026-02-01 00:00:00', '2026-12-31 23:59:59', 'active');

-- ===========================
-- Users
-- ===========================
INSERT INTO users (user_id, email, user_name, password_hash, is_active, created_at, full_name, is_provisional) VALUES
  (1, 'brad.petz@gmail.com', 'leyzer', '$2b$12$7N/xIe3sfwVni6idkZqECeeZxWSWaupfOlhqb7SQPGwOmed/gwkFu', 1, '2026-02-13 18:45:31', 'Bradley Petzer', 0);

-- ===========================
-- User Roles
-- ===========================
INSERT INTO user_roles (user_id, role) VALUES
  (1, 'admin');

-- ===========================
-- Elo Rules
-- ===========================
INSERT INTO elo_rules (elo_rule_id, category, points_band, base_rating, k_factor) VALUES
  (1, 'AOS', 'SP/CP', 400, 16),
  (2, 'AOS', '1000', 400, 24),
  (3, 'AOS', '1500', 400, 24),
  (4, 'AOS', '2000', 400, 32),
  (5, '40k', 'SP/CP', 400, 16),
  (6, '40k', '1000', 400, 24),
  (7, '40k', '1500', 400, 24),
  (8, '40k', '2000', 400, 32),
  (9, 'skirmish', 'skirmish', 400, 24),
  (10, 'mass_battle', 'mass_battle', 400, 24);

-- ===========================
-- Factions
-- ===========================
INSERT INTO factions (faction_id, system_id, faction_name) VALUES
  (1, 1, 'Cities of Sigmar'),
  (2, 1, 'Daughters of Khaine'),
  (3, 1, 'Fyreslayers'),
  (4, 1, 'Idoneth Deepkin'),
  (5, 1, 'Kharadron Overlords'),
  (6, 1, 'Lumineth Realm-Lords'),
  (7, 1, 'Seraphon'),
  (8, 1, 'Stormcast Eternals'),
  (9, 1, 'Sylvaneth'),
  (10, 1, 'Flesh-eater Courts'),
  (11, 1, 'Nighthaunt'),
  (12, 1, 'Ossiarch Bonereapers'),
  (13, 1, 'Soulblight Gravelords'),
  (14, 1, 'Blades of Khorne'),
  (15, 1, 'Disciples of Tzeentch'),
  (16, 1, 'Hedonites of Slaanesh'),
  (17, 1, 'Helsmiths of Hashut'),
  (18, 1, 'Maggotkin of Nurgle'),
  (19, 1, 'Skaven'),
  (20, 1, 'Slaves to Darkness'),
  (21, 1, 'Gloomspite Gitz'),
  (22, 1, 'Ogor Mawtribes'),
  (23, 1, 'Orruk Warclans'),
  (24, 1, 'Sons of Behemat'),
  (25, 2, 'Space Marines'),
  (26, 2, 'Black Templars'),
  (27, 2, 'Blood Angels'),
  (28, 2, 'Dark Angels'),
  (29, 2, 'Deathwatch'),
  (30, 2, 'Grey Knights'),
  (31, 2, 'Imperial Fists'),
  (32, 2, 'Iron Hands'),
  (33, 2, 'Raven Guard'),
  (34, 2, 'Salamanders'),
  (35, 2, 'Space Wolves'),
  (36, 2, 'Ultramarines'),
  (37, 2, 'White Scars'),
  (38, 2, 'Adepta Sororitas'),
  (39, 2, 'Adeptus Custodes'),
  (40, 2, 'Adeptus Mechanicus'),
  (41, 2, 'Astra Militarum'),
  (42, 2, 'Imperial Agents'),
  (43, 2, 'Imperial Knights'),
  (44, 2, 'Chaos Daemons'),
  (45, 2, 'Chaos Knights'),
  (46, 2, 'Chaos Space Marines'),
  (47, 2, 'Death Guard'),
  (48, 2, 'Emperor''s Children'),
  (49, 2, 'Thousand Sons'),
  (50, 2, 'World Eaters'),
  (51, 2, 'Aeldari'),
  (52, 2, 'Drukhari'),
  (53, 2, 'Genestealer Cults'),
  (54, 2, 'Leagues of Votann'),
  (55, 2, 'Necrons'),
  (56, 2, 'Orks'),
  (57, 2, 'Tau Empire'),
  (58, 2, 'Tyranids');


