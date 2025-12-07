def extract(processor):
    s2_data = {
        'damage_values': [],
        'idle_values': []
    }
    
    for f in processor.fights:
        s2_data['damage_values'].append(f['damage_total'])
        
        for idle_val in f['idle_pre'].values():
            s2_data['idle_values'].append(idle_val)
            
    return s2_data