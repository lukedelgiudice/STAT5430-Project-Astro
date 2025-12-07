def extract(processor):
    raw_winner = processor.json_data.get('winner')
    winning_team = processor.json_data.get('winning team')
    
    meta = {
        'map': processor.json_data.get('Map', 'Unknown'),
        'mode': processor.json_data.get('GameMode', 'Unknown'),
        'duration': processor.json_data.get('DurationSec', 0),
        'winner_name': raw_winner,
        'winning_team_id': winning_team
    }
    
    return meta