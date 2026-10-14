# Provenance

- Source: https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip
- Licence: CC0 1.0 (https://github.com/dcaribou/transfermarkt-datasets)
- Downloaded (UTC): 2026-10-14T18:44:17Z
- Archive: 241129627 bytes, SHA-256 ae2270f7820e09329c423a12562f4494e237d0dc1a4624cff21df050e79d5a18
- Filter: league games in GB1, ES1, L1, IT1, FR1 dated 2023-07-01 or later, their players, valuations from 2022-07-01

| File | Rows kept | Columns |
|---|---|---|
| games.csv.gz | 5256 | game_id, competition_id, season, round, date, home_club_id, away_club_id, home_club_goals, away_club_goals, home_club_position, away_club_position, home_club_manager_name, away_club_manager_name, stadium, attendance, referee, url, home_club_formation, away_club_formation, home_club_name, away_club_name, aggregate, competition_type |
| appearances.csv.gz | 162694 | appearance_id, game_id, player_id, player_club_id, player_current_club_id, date, player_name, competition_id, yellow_cards, red_cards, goals, assists, minutes_played |
| game_lineups.csv.gz | 222413 | game_lineups_id, date, game_id, player_id, club_id, player_name, type, position, number, team_captain |
| club_games.csv.gz | 10512 | game_id, club_id, own_goals, own_position, own_manager_name, opponent_id, opponent_goals, opponent_position, opponent_manager_name, hosting, is_win |
| players.csv.gz | 4330 | player_id, first_name, last_name, name, last_season, current_club_id, player_code, country_of_birth, city_of_birth, country_of_citizenship, date_of_birth, sub_position, position, foot, height_in_cm, contract_expiration_date, agent_name, image_url, international_caps, international_goals, current_national_team_id, url, current_club_domestic_competition_id, current_club_name, market_value_in_eur, highest_market_value_in_eur |
| player_valuations.csv.gz | 37609 | player_id, date, market_value_in_eur, current_club_name, current_club_id, player_club_domestic_competition_id |
| clubs.csv.gz | 796 | club_id, club_code, name, domestic_competition_id, total_market_value, squad_size, average_age, foreigners_number, foreigners_percentage, national_team_players, stadium_name, stadium_seats, net_transfer_record, coach_name, last_season, filename, url |
| competitions.csv.gz | 65 | competition_id, competition_code, name, sub_type, type, country_id, country_name, domestic_league_code, confederation, total_clubs, url |
