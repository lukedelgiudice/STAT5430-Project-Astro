def extract(processor):
    s11_fight_starts = []
    
    for f in processor.fights:
        p_list = list(f['participants_user'])
        if p_list:
            u1 = p_list[0]
            raw_id_u1 = None
            if u1 in processor.username_map:
                for rid in processor.username_map[u1]:
                    if processor.resolve_user(rid, f['start_stamp']) == u1:
                        raw_id_u1 = rid
                        break
            
            if raw_id_u1 is not None:
                 row = processor.df_update[
                    (processor.df_update['PlayerId'] == raw_id_u1) & 
                    (abs(processor.df_update['Stamp'] - f['start_stamp']) < 200)
                 ]
                 if not row.empty:
                     loc = [row.iloc[0]['Location.X'], row.iloc[0]['Location.Y'], row.iloc[0]['Location.Z']]
                     s11_fight_starts.append({
                         'loc': loc,
                         'item': f['items'][0] if f['items'] else 'Default'
                     })
                     
    return s11_fight_starts