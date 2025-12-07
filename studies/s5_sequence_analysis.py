import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import os
from config import OUTPUT_DIR

def run(data):
    all_S5 = []
    for d in data: 
        if 'S5' in d:
            all_S5.extend(d['S5'])
    
    ngram_counts_kill = defaultdict(int)
    ngram_counts_death = defaultdict(int)
    
    total_kills = 0
    total_deaths = 0
    
    for entry in all_S5:
        outcome = entry['result']
        seq = entry['sequence']
        
        if len(seq) < 2:
            continue
        
        if outcome == 'kill':
            total_kills += 1
            for i in range(len(seq)-1):
                ngram_counts_kill[f"{seq[i]} -> {seq[i+1]}"] += 1
                
        elif outcome == 'death':
            total_deaths += 1
            for i in range(len(seq)-1):
                ngram_counts_death[f"{seq[i]} -> {seq[i+1]}"] += 1

    rows = []
    
    # Process Top Kills
    if total_kills > 0:
        top_kill = sorted(ngram_counts_kill.items(), key=lambda x: x[1], reverse=True)[:10]
        for pat, count in top_kill:
            rows.append({
                'Pattern': pat, 
                'Count': count, 
                'Frequency': count / total_kills, 
                'Outcome': 'Kill'
            })

    # Process Top Deaths
    if total_deaths > 0:
        top_death = sorted(ngram_counts_death.items(), key=lambda x: x[1], reverse=True)[:10]
        for pat, count in top_death:
            rows.append({
                'Pattern': pat, 
                'Count': count, 
                'Frequency': count / total_deaths,
                'Outcome': 'Death'
            })

    if rows:
        df_patterns = pd.DataFrame(rows)
        df_patterns.to_csv(os.path.join(OUTPUT_DIR, "data", "s6_sequential_patterns.csv"), index=False)
        
        plt.figure(figsize=(12, 8))
        sns.barplot(
            data=df_patterns, 
            y='Pattern', 
            x='Frequency', 
            hue='Outcome', 
            palette={'Kill': 'forestgreen', 'Death': 'crimson'}
        )
        
        plt.title(f"Movement Sequences Leading to Success vs Failure\n(Kills={total_kills}, Deaths={total_deaths})")
        plt.xlabel("Frequency (Occurrences per Event)")
        plt.ylabel("Event Sequence (2-Gram)")
        plt.grid(True, axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s6_sequence_mining.png"))
        plt.close()
    else:
        print("s6 skipped: No sequences found.")