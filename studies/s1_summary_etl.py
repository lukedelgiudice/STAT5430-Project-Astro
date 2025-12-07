import numpy as np
from config import STAMPS_PER_SECOND, STAMPS_THRESHOLD, CSV_SAMPLE_COUNT

def extract(processor):
    raw_winner = processor.json_data.get('winner')
    winning_team = processor.json_data.get('winning team')
    
    s1_meta = {
        'map': processor.json_data.get('Map', 'Unknown'),
        'mode': processor.json_data.get('GameMode', 'Unknown'),
        'duration': processor.json_data.get('DurationSec', 0),
        'winner_name': raw_winner,
        'winning_team_id': winning_team
    }

    user_teams = {} 
    for e in processor.events:
        if e.get('name') == 'set_team':
            raw_id = e.get('player')
            team_id = e.get('team')
            t = e.get('stamp')
            u = processor.resolve_user(raw_id, t)
            user_teams[u] = team_id

    s1_settings = []
    device_profiles = processor.json_data.get('DeviceProfiles', [])
    for profile in device_profiles:
        s1_settings.append({
            'gpu': profile.get('GPU', {}).get('Name'),
            'res_x': profile.get('Settings', {}).get('ResX'),
            'res_y': profile.get('Settings', {}).get('ResY'),
            'window_mode': profile.get('Settings', {}).get('WindowMode'),
            'fps_cap': profile.get('Settings', {}).get('FrameRateLimit') 
        })

    s1_players = {}
    all_users = set(processor.username_map.keys())

    for user in all_users:
        raw_ids = processor.username_map[user]
        
        did_win = 0
        if winning_team is not None:
            if user_teams.get(user, -1) == winning_team:
                did_win = 1
        elif raw_winner:
            if user == raw_winner:
                did_win = 1
            elif isinstance(raw_winner, int):
                 if processor.resolve_user(raw_winner, s1_meta['duration']) == user:
                     did_win = 1
        
        kills = 0
        deaths = 0
        for e in processor.events:
            if e.get('name') == 'elim':
                if processor.resolve_user(e.get('instigator'), e.get('stamp')) == user:
                    if e.get('instigator') != e.get('target'):
                        kills += 1
                if processor.resolve_user(e.get('target'), e.get('stamp')) == user:
                    deaths += 1
        
        playtime_sec = 0
        for raw_id in raw_ids:
            if raw_id in processor.id_history:
                for seg in processor.id_history[raw_id]:
                    if seg['user'] == user:
                        end = min(seg['end'], processor.events[-1].get('stamp', 0))
                        playtime_sec += (end - seg['start']) / STAMPS_PER_SECOND

        s1_players[user] = {
            'kills': kills,
            'deaths': deaths,
            'playtime': playtime_sec,
            'won': did_win,
            'team': user_teams.get(user, -1)
        }

    s1_items = {} 
    def get_item_entry(name):
        if name not in s1_items:
            s1_items[name] = {'swaps':0, 'kills_final':0, 'kills_held':0, 'deaths_held':0, 'time_held':0, 'first_picks':0, 'suicides':0}
        return s1_items[name]

    first_pick_tracked = set()
    
    for e in processor.events:
        t = e.get('stamp')
        ename = e.get('name')
        
        if ename in ['equip']:
            item = e.get('item', 'Default')
            user = processor.resolve_user(e.get('player'), t)
            get_item_entry(item)['swaps'] += 1
            if user not in first_pick_tracked:
                get_item_entry(item)['first_picks'] += 1
                first_pick_tracked.add(user)

        elif ename == 'elim':
            instigator_id = e.get('instigator')
            target_id = e.get('target')
            final_blow_item = e.get('item', 'Unknown')
            
            if instigator_id is not None and target_id is not None:
                if instigator_id == target_id:
                    get_item_entry(final_blow_item)['suicides'] += 1
                else:
                    get_item_entry(final_blow_item)['kills_final'] += 1
                    held_item_k = processor.get_weapon_at_time(instigator_id, t)
                    get_item_entry(held_item_k)['kills_held'] += 1
                    held_item_d = processor.get_weapon_at_time(target_id, t)
                    get_item_entry(held_item_d)['deaths_held'] += 1

    timeline_by_pid = {}
    for entry in processor.weapon_timeline:
        pid = entry['pid']
        if pid not in timeline_by_pid: timeline_by_pid[pid] = []
        timeline_by_pid[pid].append(entry)
        
    for pid, entries in timeline_by_pid.items():
        for i in range(len(entries)):
            current = entries[i]
            start_t = current['time']
            item = current['item']
            
            if i < len(entries) - 1:
                end_t = entries[i+1]['time']
            else:
                session_end = processor.events[-1].get('stamp')
                if pid in processor.id_history:
                    for seg in processor.id_history[pid]:
                        if seg['start'] <= start_t <= seg['end']:
                            session_end = seg['end']
                            break
                end_t = min(session_end, processor.events[-1].get('stamp'))

            duration_sec = max(0, (end_t - start_t) / STAMPS_PER_SECOND)
            get_item_entry(item)['time_held'] += duration_sec

    s1_dist = {'roll_angles': [], 'speeds': [], 'kill_speeds': [], 'lifespans': []}
    
    if not processor.df_update.empty:
        sample = processor.df_update.iloc[::CSV_SAMPLE_COUNT]
        if 'Rotation.Roll' in sample.columns:
            s1_dist['roll_angles'] = sample['Rotation.Roll'].tolist()
        if 'Velocity.X' in sample.columns:
            vels = sample[['Velocity.X', 'Velocity.Y', 'Velocity.Z']].values
            speeds = np.linalg.norm(vels, axis=1)
            s1_dist['speeds'] = speeds.tolist()

    for e in processor.events:
        if e.get('name') == 'elim':
            killer_id = e.get('instigator')
            t = e.get('stamp')
            row = processor.df_update[
                (processor.df_update['PlayerId'] == killer_id) & 
                (abs(processor.df_update['Stamp'] - t) < STAMPS_THRESHOLD)
            ]
            if not row.empty:
                v = row.iloc[0][['Velocity.X', 'Velocity.Y', 'Velocity.Z']].values
                speed = np.linalg.norm(v)
                s1_dist['kill_speeds'].append(speed)

    active_spawns = {}
    for e in processor.events:
        ename = e.get('name', '')
        pid = e.get('player', e.get('target'))
        t = e.get('stamp')
        
        if ename == 'spawn':
            active_spawns[pid] = t
        elif ename == 'elim':
            if pid in active_spawns:
                lifespan = (t - active_spawns[pid]) / STAMPS_PER_SECOND
                s1_dist['lifespans'].append(lifespan)
                del active_spawns[pid]

    kill_fights = [f for f in processor.fights if f['winner'] is not None]
    s1_fight_stats = {'durations': [f['duration'] for f in kill_fights]}

    s1_perf = {} 
    for username, df in processor.perf_dfs.items():
        if df is None or df.empty: continue
        
        p_stats = {
            'gpu_bound_frames': 0, 'nettick_bound_frames': 0, 'gt_bound_frames': 0,
            'total_frames': len(df), 'avg_latency': 0, 'avg_fps': 0
        }
        if 'GPU Bound' in df.columns: p_stats['gpu_bound_frames'] = int(df['GPU Bound'].sum())
        if 'GT Bound' in df.columns: p_stats['gt_bound_frames'] = int(df['GT Bound'].sum())
        if 'NTT Bound' in df.columns: p_stats['nettick_bound_frames'] = int(df['NTT Bound'].sum())
        
        if 'Packet Latency' in df.columns:
            p_stats['avg_latency'] = float(df['Packet Latency'].mean())
            p_stats['all_latencies'] = df['Packet Latency'].astype(float).tolist()
        if 'Frame Avg' in df.columns:
            avg_frame_ms = df['Frame Avg'].mean()
            p_stats['avg_fps'] = 1000.0 / avg_frame_ms if avg_frame_ms > 0 else 0

        s1_perf[username] = p_stats

    return {
        'meta': s1_meta,
        'players': s1_players,
        'items': s1_items,
        'settings': s1_settings,
        'distributions': s1_dist,
        'fight_stats': s1_fight_stats,
        'performance': s1_perf
    }