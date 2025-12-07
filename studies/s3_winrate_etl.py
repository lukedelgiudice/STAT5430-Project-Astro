from config import DEFAULT_HEALTH

def extract(processor):
    s3_rows = []
    IGNORED_ITEMS = ['Kick', 'Unknown', 'Environment', 'Grapple', 'Teleport']
    
    for f in processor.fights:
        if f['winner'] is None or len(f['participants_user']) != 2:
            continue
        
        p1, p2 = f['participants_user']
        winner_name = f['winner']
        
        if p1 not in f['participant_details'] or p2 not in f['participant_details']:
            continue
        
        d1 = f['participant_details'][p1]
        d2 = f['participant_details'][p2]
        
        p1_won = 1 if winner_name == p1 else 0
        p2_won = 1 if winner_name == p2 else 0
        
        total_dmg_p1 = d1['total_damage_dealt']
        enemy_primary = "None"
        if d2['items_used']:
            enemy_primary = max(d2['items_used'], key=d2['items_used'].get)

        for item_name, item_dmg in d1['items_used'].items():
            if item_name in IGNORED_ITEMS: continue

            if p1_won:
                attribution_weight = min(1.0, item_dmg / DEFAULT_HEALTH)
            else:
                if total_dmg_p1 > 0:
                    attribution_weight = item_dmg / total_dmg_p1
                else:
                    attribution_weight = 1.0

            s3_rows.append({
                'fight_id': f['id'], 'player': p1, 'win': p1_won,
                'attribution_weight': attribution_weight, 'item_used': item_name,
                'damage_dealt_with_item': item_dmg, 'enemy_item_primary': enemy_primary,
                'start_health': d1['start_health'], 'start_dist': f['start_dist']
            })

        total_dmg_p2 = d2['total_damage_dealt']
        enemy_primary_for_p2 = "None"
        if d1['items_used']:
            enemy_primary_for_p2 = max(d1['items_used'], key=d1['items_used'].get)

        for item_name, item_dmg in d2['items_used'].items():
            if item_name in IGNORED_ITEMS: continue

            if p2_won:
                attribution_weight = min(1.0, item_dmg / DEFAULT_HEALTH)
            else:
                if total_dmg_p2 > 0:
                    attribution_weight = item_dmg / total_dmg_p2
                else:
                    attribution_weight = 1.0

            s3_rows.append({
                'fight_id': f['id'], 'player': p2, 'win': p2_won,
                'attribution_weight': attribution_weight, 'item_used': item_name,
                'damage_dealt_with_item': item_dmg, 'enemy_item_primary': enemy_primary_for_p2,
                'start_health': d2['start_health'], 'start_dist': f['start_dist']
            })

    return s3_rows