def extract(processor):
    s5_deaths = []
    
    current_map = processor.json_data.get('Map', 'Unknown')
    
    for e in processor.events:
        if e.get('name') == 'elim':
            t = e.get('stamp')
            target_id = e.get('target')
            
            loc = e.get('location') 
            
            if not loc:
                row = processor.df_update[
                    (processor.df_update['PlayerId'] == target_id) & 
                    (abs(processor.df_update['Stamp'] - t) < 100)
                ]
                if not row.empty:
                    loc = [row.iloc[0]['Location.X'], row.iloc[0]['Location.Y'], row.iloc[0]['Location.Z']]
            
            if loc:
                s5_deaths.append({
                    'map': current_map,
                    'x': loc[0], 
                    'y': loc[1], 
                    'z': loc[2]
                })
                
    return s5_deaths