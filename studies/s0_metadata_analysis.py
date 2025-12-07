import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import os
from config import OUTPUT_DIR

def run(data):
    mode_counts = defaultdict(int)
    
    for d in data:
        if 'S0' in d:
            mode = d['S0'].get('mode', 'Unknown')
            mode_counts[mode] += 1
    
    df_modes = pd.DataFrame({
        'Game_Mode': list(mode_counts.keys()),
        'Games_Played': list(mode_counts.values())
    }).sort_values('Games_Played', ascending=False).reset_index(drop=True)
    
    total_games = len(data)
    if total_games > 0:
        df_modes['Percentage'] = (df_modes['Games_Played'] / total_games * 100).round(2)
        df_modes['Percentage'] = df_modes['Percentage'].astype(str) + '%'
    
    df_modes.to_csv(os.path.join(OUTPUT_DIR, "data", "s0_game_mode_frequency.csv"), index=False)

    if not df_modes.empty:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(range(len(df_modes)), df_modes['Games_Played'], 
                       color='steelblue', edgecolor='navy', alpha=0.85, linewidth=1.2)
        
        plt.title("Game Mode Distribution", fontsize=16, pad=20)
        plt.ylabel("Number of Games Played", fontsize=12)
        plt.xlabel("Game Mode", fontsize=12)
        plt.xticks(range(len(df_modes)), df_modes['Game_Mode'], rotation=45, ha='right')
        
        for i, bar in enumerate(bars):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + max(df_modes['Games_Played']) * 0.01,
                     f"{int(height)}", ha='center', va='bottom', fontweight='bold', fontsize=10)
        
        plt.grid(True, axis='y', alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s0_game_mode_frequency.png"), dpi=150, bbox_inches='tight')
        plt.close()
    
    #print(f"{total_games} games across {len(df_modes)} modes")