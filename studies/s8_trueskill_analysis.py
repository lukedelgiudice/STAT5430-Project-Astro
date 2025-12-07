import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import trueskill
from collections import defaultdict
import os
from config import OUTPUT_DIR

def run(data):    
    env = trueskill.TrueSkill(draw_probability=0.0) 
    ratings = defaultdict(env.create_rating)
    
    for d in data:
        if 'S8' not in d:
            continue

        player_scores = []
        
        for p, stats in d['S8'].items():
            k = stats['kills']
            d_count = stats['deaths']
            is_winner = stats.get('won', 0)
            
            score = (k - d_count) + (is_winner * 5)
            player_scores.append((p, score))
        
        player_scores.sort(key=lambda x: x[1], reverse=True)
        
        groups = [] 
        ranks = [] 
        
        current_rank = 0
        for i, (p, score) in enumerate(player_scores):
            groups.append((ratings[p],))
            if i > 0 and score < player_scores[i-1][1]:
                current_rank += 1
            ranks.append(current_rank)
        
        if len(groups) > 1:
             try:
                 rated_groups = env.rate(groups, ranks=ranks)
                 for i, (p, _) in enumerate(player_scores):
                     ratings[p] = rated_groups[i][0]
             except Exception as e:
                 print(f"TrueSkill failed for a match: {e}")
    
    rating_rows = []
    for u, r in ratings.items():
        rating_rows.append({
            'Username': u, 
            'Mu': r.mu, 
            'Sigma': r.sigma,
            'Conservative_Score': r.mu - 3*r.sigma
        })
        
    df_ratings = pd.DataFrame(rating_rows).sort_values('Mu', ascending=False)
    df_ratings.to_csv(os.path.join(OUTPUT_DIR, "data", "s8_trueskill_ratings.csv"), index=False)
    
    # Visual
    if not df_ratings.empty:
        plt.figure(figsize=(10,6))
        sns.histplot(df_ratings['Mu'], kde=True, bins=20, color='mediumpurple')
        plt.title("Distribution of Player Skill (TrueSkill Mu)\n(Based on Net Kills + Win Bonus)")
        plt.xlabel("Skill Rating (Mu)")
        plt.axvline(25, color='k', linestyle='--', alpha=0.5, label='Default Start (25)')
        plt.legend()
        plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s8_skill_dist.png"))
        plt.close()