import numpy as np
from config import STAMPS_PER_SECOND

def extract(processor):
    s7_curves = []
    
    has_velocity = 'Velocity.X' in processor.df_update.columns
    if not has_velocity:
        return []

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
            
            start_curve = t - (5 * STAMPS_PER_SECOND)
            
            for sub in subjects:
                pid = sub['pid']
                outcome = sub['outcome']
                
                w_df = processor.df_update[
                    (processor.df_update['PlayerId'] == pid) & 
                    (processor.df_update['Stamp'] >= start_curve) & 
                    (processor.df_update['Stamp'] <= t)
                ]
                
                if not w_df.empty:
                    c_vels = w_df[['Velocity.X', 'Velocity.Y', 'Velocity.Z']].values
                    c_speeds = np.linalg.norm(c_vels, axis=1).tolist()
                    
                    if len(c_speeds) == 10:
                        s7_curves.append({'result': outcome, 'curve': c_speeds})
                    
    return s7_curves