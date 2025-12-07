import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import random
import os
from config import OUTPUT_DIR

def run(data):    
    INITIAL_HEALTH_REGEN_WAIT = 5.0
    ACTIVE_HEALTH_REGEN_WAIT = 2.0
    MAX_HEALTH = 10
    N_SIMULATIONS_PER_START = 500

    all_dmg = []
    all_idle = []
    for d in data:
        all_dmg.extend(d['S2']['damage_values'])
        all_idle.extend(d['S2']['idle_values'])

    if not all_dmg or not all_idle:
        #no fight/idle data found
        return

    transition_counts = np.zeros((MAX_HEALTH + 1, MAX_HEALTH + 1))

    def simulate_next_health(start_health, damage_taken, idle_time):
        if damage_taken >= start_health:
            return MAX_HEALTH 
        
        health_after_fight = max(0, start_health - damage_taken)
        
        remaining_time = idle_time
        
        if remaining_time <= INITIAL_HEALTH_REGEN_WAIT:
            return health_after_fight
        
        remaining_time -= INITIAL_HEALTH_REGEN_WAIT
        
        regen_ticks = int(remaining_time // ACTIVE_HEALTH_REGEN_WAIT)
        final_health = health_after_fight + regen_ticks
        
        return min(final_health, MAX_HEALTH)

    for start_h in range(MAX_HEALTH + 1):
        for _ in range(N_SIMULATIONS_PER_START):
            dmg = random.choice(all_dmg)
            idle = random.choice(all_idle)
            next_h = int(simulate_next_health(start_h, dmg, idle))
            transition_counts[start_h, next_h] += 1

    row_sums = transition_counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1 
    transition_matrix = transition_counts / row_sums

    eigenvalues, eigenvectors = np.linalg.eig(transition_matrix.T)
    stationary_idx = np.argmin(np.abs(eigenvalues - 1.0))
    stationary = np.real(eigenvectors[:, stationary_idx])
    stationary = stationary / stationary.sum()

    df_trans = pd.DataFrame(
        transition_matrix,
        index=[f"Start_{h}" for h in range(MAX_HEALTH + 1)],
        columns=[f"Next_{h}" for h in range(MAX_HEALTH + 1)]
    )
    df_trans.to_csv(os.path.join(OUTPUT_DIR, "data", "s2_transition_matrix.csv"))

    df_stationary = pd.DataFrame({
        'Health': list(range(MAX_HEALTH + 1)),
        'Probability': stationary
    })
    df_stationary.to_csv(os.path.join(OUTPUT_DIR, "data", "s2_stationary_distribution.csv"), index=False)
    
    min_len = min(len(all_dmg), len(all_idle))
    df_paired = pd.DataFrame({
        'source_damage_sample': all_dmg[:min_len],
        'source_idle_sample': all_idle[:min_len]
    })
    df_paired.to_csv(os.path.join(OUTPUT_DIR, "data", "s2_source_data.csv"), index=False)

    plt.figure(figsize=(10, 6))
    plt.bar(df_stationary['Health'], df_stationary['Probability'], 
            color='teal', edgecolor='black', alpha=0.8)
    plt.title(f"Stationary Health Distribution (Stable State)\n"
              f"Wait={INITIAL_HEALTH_REGEN_WAIT}s, Regen={ACTIVE_HEALTH_REGEN_WAIT}s/hp")
    plt.xlabel("Health at Start of Fight")
    plt.ylabel("Probability")
    plt.xticks(range(0, MAX_HEALTH + 1))
    plt.grid(True, axis='y', alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s2_stationary_dist.png"))
    plt.close()

    plt.figure(figsize=(10, 8))
    sns.heatmap(transition_matrix, annot=True, fmt=".2f", cmap="Blues",
                xticklabels=range(MAX_HEALTH+1), yticklabels=range(MAX_HEALTH+1))
    plt.title("Study 2: Health Transition Probabilities")
    plt.xlabel("Next Health")
    plt.ylabel("Current Health")
    plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s2_transition_heatmap.png"))
    plt.close()
        
    plt.figure(figsize=(10,6))
    sns.histplot(all_idle, kde=True, bins=30)
    plt.title("Distribution of Time Between Fights (Idle Time)")
    plt.xlabel("Seconds")
    plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s2_idle_distribution.png"))
    plt.close()