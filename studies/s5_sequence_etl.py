import numpy as np
from config import STAMPS_PER_SECOND

def extract(processor):
    s6_sequences = []
    has_velocity = 'Velocity.X' in processor.df_update.columns

    for e in processor.events:
        if e.get('name') == 'elim':
            t = e.get('stamp')
            instigator_id = e.get('instigator')
            target_id = e.get('target')
            
            subjects = []
            if instigator_id and instigator_id != target_id:
                subjects.append({'pid': instigator_id, 'outcome': 'kill'})
            if target_id:
                subjects.append({'pid': target_id, 'outcome': 'death'})
            
            start_seq = t - (10 * STAMPS_PER_SECOND)
            
            for sub in subjects:
                pid = sub['pid']
                outcome = sub['outcome']
                
                seq_events = [
                    ev.get('name') for ev in processor.events 
                    if ev.get('player') == pid 
                    and start_seq <= ev.get('stamp') <= t 
                    and ev.get('name') in ['surface_lock', 'push_off', 'dash', 'kick']
                ]
                
                w_df = processor.df_update[
                    (processor.df_update['PlayerId'] == pid) & 
                    (processor.df_update['Stamp'] >= start_seq) & 
                    (processor.df_update['Stamp'] <= t)
                ]
                
                if not w_df.empty and has_velocity:
                    vels = w_df[['Velocity.X', 'Velocity.Y', 'Velocity.Z']].values
                    speeds = np.linalg.norm(vels, axis=1)
                    if np.max(speeds) > 1500: seq_events.append("high_velocity")
                
                s6_sequences.append({'result': outcome, 'sequence': seq_events})
                
    return s6_sequences