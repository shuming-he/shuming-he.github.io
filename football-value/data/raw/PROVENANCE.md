# Provenance

- Source: https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfermarkt-datasets.zip
- Downloaded (UTC): 2026-10-14T18:42:46Z
- Archive size: 241129627 bytes, SHA-256 ae2270f7820e09329c423a12562f4494e237d0dc1a4624cff21df050e79d5a18

| File | Bytes | Rows | Columns |
|---|---|---|---|
| appearances.csv.gz | 198398405 | 1894350 | appearance_id, game_id, player_id, player_club_id, player_current_club_id, date, player_name, competition_id, yellow_cards, red_cards, goals, assists, minutes_played |
| club_games.csv.gz | 14748080 | 177916 | game_id, club_id, own_goals, own_position, own_manager_name, opponent_id, opponent_goals, opponent_position, opponent_manager_name, hosting, is_win |
| clubs.csv.gz | 208374 | 796 | club_id, club_code, name, domestic_competition_id, total_market_value, squad_size, average_age, foreigners_number, foreigners_percentage, national_team_players, stadium_name, stadium_seats, net_transfer_record, coach_name, last_season, filename, url |
| competitions.csv.gz | 12247 | 65 | competition_id, competition_code, name, sub_type, type, country_id, country_name, domestic_league_code, confederation, total_clubs, url |
| countries.csv.gz | 15058 | 124 | country_id, country_name, country_code, confederation, total_clubs, total_players, average_age, url |
| game_events.csv.gz | 179098694 | 1274469 | game_event_id, date, game_id, minute, type, club_id, club_name, player_id, description, player_in_id, player_assist_id |
| game_lineups.csv.gz | 415978884 | 3179016 | game_lineups_id, date, game_id, player_id, club_id, player_name, type, position, number, team_captain |
| games.csv.gz | 28965132 | 88958 | game_id, competition_id, season, round, date, home_club_id, away_club_id, home_club_goals, away_club_goals, home_club_position, away_club_position, home_club_manager_name, away_club_manager_name, stadium, attendance, referee, url, home_club_formation, away_club_formation, home_club_name, away_club_name, aggregate, competition_type |
| national_teams.csv.gz | 32980 | 124 | national_team_id, name, team_code, country_id, country_name, country_code, confederation, team_image_url, squad_size, average_age, foreigners_number, foreigners_percentage, total_market_value, coach_name, fifa_ranking, last_season, url |
| player_valuations.csv.gz | 39647280 | 656301 | player_id, date, market_value_in_eur, current_club_name, current_club_id, player_club_domestic_competition_id |
| players.csv.gz | 19624138 | 50149 | player_id, first_name, last_name, name, last_season, current_club_id, player_code, country_of_birth, city_of_birth, country_of_citizenship, date_of_birth, sub_position, position, foot, height_in_cm, contract_expiration_date, agent_name, image_url, international_caps, international_goals, current_national_team_id, url, current_club_domestic_competition_id, current_club_name, market_value_in_eur, highest_market_value_in_eur |
| transfers.csv.gz | 18112063 | 175165 | player_id, transfer_date, transfer_season, from_club_id, to_club_id, from_club_name, to_club_name, transfer_fee, market_value_in_eur, player_name |
