from config import STAMPS_PER_SECOND

def extract(processor):
    s4_paths = []
    
    for raw_id, segments in processor.id_history.items():
        for seg in segments:
            user = seg['user']
            
            session_df = processor.df_update[
                (processor.df_update['PlayerId'] == raw_id) & 
                (processor.df_update['Stamp'] >= seg['start']) & 
                (processor.df_update['Stamp'] <= seg['end'])
            ]
            
            if session_df.empty: continue
            
            user_spawns = [t for t in processor.spawn_index.get(raw_id, []) 
                           if seg['start'] <= t <= seg['end']]
            
            for i, spawn_t in enumerate(user_spawns):
                next_t = user_spawns[i+1] if i + 1 < len(user_spawns) else seg['end']
                
                path_slice = session_df[
                    (session_df['Stamp'] >= spawn_t) & 
                    (session_df['Stamp'] < next_t)
                ]
                
                if not path_slice.empty:
                    resampled = path_slice.iloc[::int(STAMPS_PER_SECOND / 4)]
                    coords = resampled[['Location.X', 'Location.Y', 'Location.Z']].values.tolist()
                    if coords:
                        s4_paths.append({'user': user, 'path': coords})
                        
    return s4_paths