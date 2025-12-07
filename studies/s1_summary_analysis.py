import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import squarify
import matplotlib.cm
import matplotlib.colors
from collections import defaultdict
import os
from config import OUTPUT_DIR

def run(data):    
    s1_items = defaultdict(lambda: defaultdict(int))
    s1_player_totals = defaultdict(lambda: {'kills':0, 'deaths':0, 'playtime':0, 'wins':0, 'games':0})
    s1_settings = []
    
    for d in data:
        s1 = d['S1']
        for user, stats in s1['players'].items():
            s1_player_totals[user]['kills'] += stats['kills']
            s1_player_totals[user]['deaths'] += stats['deaths']
            s1_player_totals[user]['playtime'] += stats['playtime']
            s1_player_totals[user]['wins'] += stats['won']
            s1_player_totals[user]['games'] += 1
        
        for item, metrics in s1['items'].items():
            for k, v in metrics.items():
                s1_items[item][k] += v
        
        s1_settings.extend(s1['settings'])

    df_players = pd.DataFrame.from_dict(s1_player_totals, orient='index').reset_index()
    df_players.rename(columns={'index':'Username'}, inplace=True)
    df_players['WinRate'] = df_players['wins'] / df_players['games']
    df_players['K/D'] = df_players['kills'] / df_players['deaths'].replace(0, 1)
    df_players.to_csv(os.path.join(OUTPUT_DIR, "data", "s1_player_stats.csv"), index=False)

    item_rows = []
    for item, m in s1_items.items():
        row = m.copy()
        row['Item'] = item
        row['KD_Held'] = row['kills_held'] / (row['deaths_held'] if row['deaths_held'] > 0 else 1)
        item_rows.append(row)
    
    df_items = pd.DataFrame(item_rows)
    df_items.to_csv(os.path.join(OUTPUT_DIR, "data", "s1_item_stats.csv"), index=False)

    if not df_items.empty:
        plt.figure(figsize=(16, 9))
        
        df_tree = df_items[df_items['kills_final'] > 0].copy()
        if not df_tree.empty:
            cmap = matplotlib.cm.RdYlGn
            norm = matplotlib.colors.Normalize(vmin=df_tree['KD_Held'].min(), vmax=df_tree['KD_Held'].max())
            colors = [cmap(norm(val)) for val in df_tree['KD_Held']]
            
            labels = [f"{r['Item']}\nKills: {r['kills_final']}\nK/D: {r['KD_Held']:.2f}" for i, r in df_tree.iterrows()]
            
            squarify.plot(sizes=df_tree['kills_final'], label=labels, color=colors, alpha=0.8, pad=True)
            plt.title("Study 1: Item Treemap\nSize=Total Kills, Color=K/D (Green=High)")
            plt.axis('off')
            plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s1_item_treemap.png"))
            plt.close()
    
        if s1_settings:
            df_set = pd.DataFrame(s1_settings)
            
            if 'fps_cap' in df_set.columns:
                df_set['fps_cap'] = df_set['fps_cap'].fillna(0).astype(int)
                
                df_set['FPS_Label'] = df_set['fps_cap'].apply(
                    lambda x: 'Uncapped' if x == 0 else str(x)
                )
                
                observed_counts = df_set['FPS_Label'].value_counts()
                
                numeric_labels = sorted(
                    [label for label in observed_counts.index if label != 'Uncapped'],
                    key=int
                )
                final_order = numeric_labels + (['Uncapped'] if 'Uncapped' in observed_counts else [])
                
                plt.figure(figsize=(11, 7))
                ax = sns.barplot(
                    x=final_order,
                    y=[observed_counts.get(label, 0) for label in final_order],
                    palette='mako',
                    edgecolor='black',
                    linewidth=1.2
                )
                
                for i, count in enumerate([observed_counts.get(label, 0) for label in final_order]):
                    ax.text(i, count + max(observed_counts) * 0.02, str(count),
                            ha='center', va='bottom', fontweight='bold', fontsize=11)
                
                plt.title("Distribution of Player FPS Caps", fontsize=16, pad=20)
                plt.xlabel("FPS Limit", fontsize=12)
                plt.ylabel("Number of Players", fontsize=12)
                plt.grid(True, axis='y', alpha=0.3, linestyle='--')
                plt.tight_layout()
                plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s1_settings_fps.png"), dpi=150)
                plt.close()
                
                #print(f"  FPS Cap plot: {len(final_order)} categories shown (including Uncapped)")