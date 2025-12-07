import os
import pandas as pd
import numpy as np
import json
import re
from config import *

class GameProcessor:
    def __init__(self, game_id, json_path, update_path, perf_paths_list):
        self.game_id = game_id
        self.json_data = self._load_clean_json(json_path)
        self.df_update = pd.read_csv(update_path)
        self.df_update.columns = self.df_update.columns.str.strip()
        self.perf_dfs = {}
        
        if perf_paths_list:
            for path in perf_paths_list:
                try:
                    filename = os.path.basename(path)
                    match = re.search(r"Performance_(.*?)_" + re.escape(game_id), filename)
                    if match:
                        username = match.group(1)
                        self.perf_dfs[username] = pd.read_csv(path)
                        self.perf_dfs[username].columns = self.perf_dfs[username].columns.str.strip()
                except Exception as e:
                    print(f"error loading perf file {path}: {e}")        

        self.events = list(self.json_data.get('events', []))
        self.id_map = {}           
        self.username_map = {}    
        self.player_loadouts = {} 
        self.fights = []           
        self.metrics = {}
        
        self._reconstruct_gamestate()
        self.detect_fights()

    def _load_clean_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f: raw = f.read()
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='utf-16') as f: raw = f.read()
            except:
                with open(path, 'r', encoding='utf-16-le') as f: raw = f.read()

        raw = raw.strip()
        if not raw: return {}

        fixed = re.sub(r'(\d+)\.(\s*[,\]\}])', r'\1.0\2', raw)
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return {}

    def _reconstruct_gamestate(self):
        self.id_history = {} 
        self.username_map = {}
        self.spawn_index = {}

        max_time = self.events[-1].get('stamp', 99999999) if self.events else 999999

        for e in self.events:
            t = e.get('stamp')
            eid = e.get('id')
            etype = e.get('name')

            if etype == 'spawn':
                pid = e.get('player')
                if pid not in self.spawn_index: self.spawn_index[pid] = []
                self.spawn_index[pid].append(t)

            if etype == 'join':
                username = e.get('username')
                if eid not in self.id_history: self.id_history[eid] = []
                if self.id_history[eid]:
                    last_entry = self.id_history[eid][-1]
                    if last_entry['end'] >= t: last_entry['end'] = t

                self.id_history[eid].append({'start': t, 'end': max_time, 'user': username})
                
                if username not in self.username_map: self.username_map[username] = []
                if eid not in self.username_map[username]: self.username_map[username].append(eid)

            elif etype in ['leave'] and eid is not None:
                if eid in self.id_history:
                    for entry in reversed(self.id_history[eid]):
                        if entry['start'] <= t and entry['end'] >= t:
                            entry['end'] = t
                            break

        unique_csv_ids = self.df_update['PlayerId'].unique()
        for uid in unique_csv_ids:
            if uid not in self.id_history:
                 self.id_history[uid] = [{'start': 0, 'end': max_time, 'user': f"Unknown_{uid}"}]

        self.weapon_timeline = []
        
        for e in self.events:
            t = e.get('stamp')
            pid = e.get('player')
            if pid is None:
                continue
            
            if e.get('name') in ['equip']: 
                item = e.get('item', 'Default')
                self.weapon_timeline.append({'time': t, 'pid': pid, 'item': item})
            
        self.df_weapons = pd.DataFrame(self.weapon_timeline)

    def get_weapon_at_time(self, pid, timestamp):
        if self.df_weapons.empty:
            return "Default"
        session_start = self.get_id_session_start(pid, timestamp)
        relevant = self.df_weapons[
            (self.df_weapons['pid'] == pid) & 
            (self.df_weapons['time'] >= session_start) & 
            (self.df_weapons['time'] <= timestamp)
        ]
        if relevant.empty: return "Default"
        return relevant.iloc[-1]['item']

    def get_id_session_start(self, raw_id, timestamp):
        if raw_id not in self.id_history:
            return 0
        for segment in self.id_history[raw_id]:
            if segment['start'] <= timestamp <= segment['end']:
                return segment['start']
        return self.id_history[raw_id][-1]['start']

    def resolve_user(self, raw_id, timestamp):
        if raw_id not in self.id_history:
            return f"Unknown_{raw_id}"
        for segment in self.id_history[raw_id]:
            if segment['start'] <= timestamp <= segment['end']:
                return segment['user']
        return self.id_history[raw_id][-1]['user']

    def detect_fights(self):
        LOOKBACK_STAMPS = 120
        TIMEOUT_STAMPS = 240
        
        actions_by_player = {}
        for e in self.events:
            if e.get('name') in ['fire', 'throw', 'swing', 'stab', 'burst']:
                pid = e.get('player')
                if pid is not None:
                    if pid not in actions_by_player: actions_by_player[pid] = []
                    actions_by_player[pid].append(e.get('stamp'))
        
        relevant_types = {'damage', 'fire', 'throw', 'swing', 'stab', 'burst', 'elim'}
        timeline = sorted(
            [e for e in self.events if e.get('name') in relevant_types], 
            key=lambda x: x.get('stamp', 0)
        )
        
        active_fights = {} 
        finished_fights = []
        
        for e in timeline:
            etype = e.get('name')
            t = e.get('stamp')
            
            to_close = []
            for pair, fight in active_fights.items():
                if t > fight['last_action_time'] + TIMEOUT_STAMPS:
                    fight['end_reason'] = 'timeout'
                    fight['end_time'] = fight['last_action_time']
                    finished_fights.append(fight)
                    to_close.append(pair)
            for pair in to_close:
                del active_fights[pair]

            if etype in ['fire', 'throw', 'swing', 'burst', 'stab']:
                pid = e.get('player')
                for pair, fight in active_fights.items():
                    if pid in pair:
                        fight['last_action_time'] = t
                        
            elif etype == 'damage':
                p1 = e.get('instigator')
                p2 = e.get('target')
                if p1 is None or p2 is None or p1 == p2:
                    continue
                if p1 not in self.id_history or p2 not in self.id_history:
                    continue

                pair = frozenset({p1, p2})
                dmg_val = e.get('damage', 0)
                item_used = e.get('item', 'Unknown')

                if item_used == 'Unknown':
                    causer = e.get('causer') or ""
                    mapping = {
                        'Boomerang': 'Boomerang', 'Throwing Star': 'ThrowingStar',
                        'Rocket': 'RocketLauncher', 'Sledge': 'Sledge',
                        'Net': 'Net', 'Projectile': 'Ripper', 'KinematicStar': 'Environment'
                    }
                    for key, value in mapping.items():
                        if key in causer:
                            item_used = value
                            break
                    if item_used == 'Unknown':
                        if ('MapCollider' in causer) or ('Astronaut' in causer):
                            item_used = 'Kick'

                if pair in active_fights:
                    active_fights[pair]['last_action_time'] = t
                    active_fights[pair]['events'].append(e)
                    active_fights[pair]['damage_total'] += dmg_val
                    
                    if p1 not in active_fights[pair]['damage_by_player_item']:
                        active_fights[pair]['damage_by_player_item'][p1] = {}
                    
                    current_item_dmg = active_fights[pair]['damage_by_player_item'][p1].get(item_used, 0)
                    active_fights[pair]['damage_by_player_item'][p1][item_used] = current_item_dmg + dmg_val

                else:
                    candidates = []
                    start_window = t - LOOKBACK_STAMPS
                    for pid in pair:
                        p_acts = actions_by_player.get(pid, [])
                        for act_t in p_acts:
                            if act_t > t:
                                break 
                            if act_t >= start_window:
                                candidates.append(act_t)
                    
                    actual_start = min(candidates) if candidates else t
                    
                    dmg_dict = {p1: {item_used: dmg_val}, p2: {}}

                    active_fights[pair] = {
                        'fight_id': f"{self.game_id}_{len(finished_fights) + len(active_fights)}",
                        'start_time': actual_start,
                        'last_action_time': t,
                        'participants': pair,
                        'events': [e],
                        'damage_total': dmg_val,
                        'damage_by_player_item': dmg_dict,
                        'end_reason': 'active',
                        'winner': None 
                    }

            elif etype == 'elim':
                pid = e.get('target')
                to_close = []
                for pair, fight in active_fights.items():
                    if pid in pair:
                        fight['end_reason'] = 'death'
                        fight['end_time'] = t 
                        
                        others = list(pair)
                        others.remove(pid)
                        fight['winner'] = others[0] if others else None
                        
                        finished_fights.append(fight)
                        to_close.append(pair)
                for pair in to_close:
                    del active_fights[pair]

        for fight in active_fights.values():
            fight['end_reason'] = 'timeout'
            fight['end_time'] = fight['last_action_time']
            finished_fights.append(fight)
            
        self.fights = []
        for f in finished_fights:
            self._finalize_fight(f)

    def _finalize_fight(self, fight_data):
        start_t = fight_data['start_time']
        end_t = fight_data['end_time']
        duration = max(0, (end_t - start_t) / STAMPS_PER_SECOND)
        
        raw_participants = list(fight_data['participants'])
        user_participants = [self.resolve_user(p, start_t) for p in raw_participants]
        
        winner_id = fight_data.get('winner')
        winner_user = self.resolve_user(winner_id, end_t) if winner_id is not None else None

        start_frame = self.df_update[
            (self.df_update['Stamp'] >= start_t - STAMPS_THRESHOLD) & 
            (self.df_update['Stamp'] <= start_t + STAMPS_THRESHOLD)
        ]

        participant_details = {} 
        start_healths = {} 
        positions = {}
        idle_times = {}
        items_used = []

        for i, raw_pid in enumerate(raw_participants):
            uname = user_participants[i]
            
            last_fight_end = -999999
            for f in reversed(self.fights):
                if uname in f['participants_user'] and f['end_stamp'] < start_t:
                    last_fight_end = f['end_stamp']
                    break
            
            last_spawn = -999999
            session_start = self.get_id_session_start(raw_pid, start_t)
            if raw_pid in self.spawn_index:
                for s_time in reversed(self.spawn_index[raw_pid]):
                    if s_time <= start_t:
                        if s_time < session_start:
                            break
                        last_spawn = s_time
                        break
            
            ref_time = max(last_fight_end, last_spawn)
            if ref_time == -999999:
                ref_time = session_start
            idle_seconds = max(0, (start_t - ref_time) / STAMPS_PER_SECOND)
            idle_times[uname] = idle_seconds

            # 2. State & Items
            items_damage_dict = fight_data['damage_by_player_item'].get(raw_pid, {})
            held_item = self.get_weapon_at_time(raw_pid, start_t)
            items_used.append(held_item) 

            if not items_damage_dict:
                items_damage_dict = {held_item: 0}

            health = DEFAULT_HEALTH
            pos = np.array([0,0,0])
            p_rows = start_frame[start_frame['PlayerId'] == raw_pid]
            if not p_rows.empty:
                row = p_rows.iloc[0]
                health = row['Health']
                pos = np.array([row['Location.X'], row['Location.Y'], row['Location.Z']])
            
            start_healths[uname] = health
            positions[raw_pid] = pos

            participant_details[uname] = {
                'items_used': items_damage_dict,
                'total_damage_dealt': sum(items_damage_dict.values()),
                'start_health': health,
                'start_pos': pos.tolist()
            }

        for e in fight_data['events']:
            if e.get('name') == 'damage':
                raw_target = e.get('target')
                p_health = e.get('prev_health')
                if raw_target is not None and p_health is not None:
                    target_user = self.resolve_user(raw_target, start_t)
                    start_healths[target_user] = p_health
                    if target_user in participant_details:
                        participant_details[target_user]['start_health'] = p_health
                break

        dist = 0
        if len(positions) >= 2:
            p1, p2 = raw_participants[:2]
            if p1 in positions and p2 in positions:
                dist = np.linalg.norm(positions[p1] - positions[p2])

        fight_obj = {
            'id': fight_data['fight_id'],
            'start_stamp': start_t,
            'end_stamp': end_t,
            'duration': duration,
            'idle_pre': idle_times, 
            'participants_user': user_participants,
            'participant_details': participant_details,
            'items': items_used,
            'start_dist': dist,
            'start_healths': start_healths,
            'winner': winner_user,
            'damage_total': fight_data['damage_total'],
            'end_reason': fight_data['end_reason']
        }
        self.fights.append(fight_obj)