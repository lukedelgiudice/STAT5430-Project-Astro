import numpy as np
from config import HIGH_SPEED_THRESHOLD, STAMPS_PER_SECOND

def extract(processor):
    s12_profiles = {}
    all_users = set(processor.username_map.keys())
    
    user_playtimes = {}
    for user in all_users:
        playtime_sec = 0
        raw_ids = processor.username_map[user]
        for raw_id in raw_ids:
            if raw_id in processor.id_history:
                for seg in processor.id_history[raw_id]:
                    if seg['user'] == user:
                        end = min(seg['end'], processor.events[-1].get('stamp', 0))
                        playtime_sec += (end - seg['start']) / STAMPS_PER_SECOND
        user_playtimes[user] = playtime_sec

    for user in all_users:
        raw_ids = processor.username_map[user]
        
        user_df = processor.df_update[processor.df_update['PlayerId'].isin(raw_ids)]
        
        high_speed_ticks = 0
        total_roll = 0
        tick_count = 0
        
        if not user_df.empty:
            vels = user_df[['Velocity.X', 'Velocity.Y', 'Velocity.Z']].values
            speeds = np.linalg.norm(vels, axis=1)
            high_speed_ticks = np.sum(speeds > HIGH_SPEED_THRESHOLD)
            
            if 'Rotation.Roll' in user_df.columns:
                total_roll = user_df['Rotation.Roll'].abs().sum()
                tick_count = len(user_df)

        dashes = 0
        for e in processor.events:
            if e.get('name') in ['dash', 'kick'] and processor.resolve_user(e.get('player'), e.get('stamp')) == user:
                dashes += 1
        
        user_fights = [f for f in processor.fights if user in f['participants_user']]
        total_dist = sum(f['start_dist'] for f in user_fights)
        fight_count = len(user_fights)
        
        playtime_m = user_playtimes[user] / 60.0
        
        s12_profiles[user] = {
            'high_speed_time': high_speed_ticks / STAMPS_PER_SECOND,
            'dashes_per_min': dashes / playtime_m if playtime_m > 0 else 0,
            'avg_roll_angle': total_roll / tick_count if tick_count > 0 else 0,
            'avg_fight_dist': total_dist / fight_count if fight_count > 0 else 0
        }
        
    return s12_profiles