import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from scipy.stats import gamma
import os
from config import OUTPUT_DIR

def run(data):    
    player_perf_history = defaultdict(lambda: {'latencies': [], 'fps_values': []})
    
    for d in data:
        s10_perf = d['S10'].get('performance', {})
        for user, stats in s10_perf.items():
            latencies_list = stats.get('all_latencies', 0)
            fps = stats.get('avg_fps', 0)
            
            if latencies_list:
                player_perf_history[user]['latencies'].extend(latencies_list)
            if fps > 0:
                player_perf_history[user]['fps_values'].append(fps)

    all_latencies = []
    all_fps = []
    agg_rows = []
    
    for user, history in player_perf_history.items():
        lats = history['latencies']
        fps_vals = history['fps_values']
        all_latencies.extend(lats)
        all_fps.extend(fps_vals)
        
        if lats or fps_vals:
            agg_rows.append({
                'Username': user,
                'Games_Recorded': len(fps_vals),
                'Avg_Latency_Global': np.mean(lats) if lats else 0,
                'Max_Latency_Global': np.max(lats) if lats else 0,
                'Avg_FPS_Global': np.mean(fps_vals) if fps_vals else 0,
                'Min_FPS_Global': np.min(fps_vals) if fps_vals else 0
            })
            
    df_perf_agg = pd.DataFrame(agg_rows)
    if not df_perf_agg.empty:
        df_perf_agg.to_csv(os.path.join(OUTPUT_DIR, "data", "s10_player_performance_aggregated.csv"), index=False)

        if all_latencies:
            plt.figure(figsize=(10, 6))
            sns.histplot(all_latencies, kde=True, color='purple', bins=30)
            plt.title("Global Player Latency Distribution")
            plt.xlabel("Average Latency per Match (ms)")
            plt.ylabel("Frequency (Player-Games)")
            
            med_lat = np.median(all_latencies)
            plt.axvline(med_lat, color='k', linestyle='--', label=f'Median: {med_lat:.1f}ms')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s10_latency_distribution.png"))
            plt.close()

            try:
                lats_clean = [x for x in all_latencies if x > 0]
                if len(lats_clean) > 5:
                    fit_alpha, fit_loc, fit_beta = gamma.fit(lats_clean)
                    p_over_100 = 1 - gamma.cdf(100, fit_alpha, loc=fit_loc, scale=fit_beta)
                    p_over_200 = 1 - gamma.cdf(200, fit_alpha, loc=fit_loc, scale=fit_beta)

                    with open(os.path.join(OUTPUT_DIR, "models", "s10_latency_gamma_params.txt"), "w") as f:
                        f.write(f"Alpha: {fit_alpha}\nLoc: {fit_loc}\nBeta: {fit_beta}")
                        f.write("\n=== PROBABILITY OF BAD LAG ===\n")
                        f.write(f"P(Avg Latency > 100 ms) = {p_over_100:.3%}\n")
                        f.write(f"P(Avg Latency > 200 ms) = {p_over_200:.3%}\n")
            except: pass

        if all_fps:
            plt.figure(figsize=(10, 6))
            sns.histplot(all_fps, kde=True, color='orange', bins=30)
            plt.title("Global Player FPS Distribution")
            plt.xlabel("Average FPS per Match")
            plt.ylabel("Frequency (Player-Games)")
            
            med_fps = np.median(all_fps)
            plt.axvline(med_fps, color='k', linestyle='--', label=f'Median: {med_fps:.1f} FPS')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s10_fps_distribution.png"))
            plt.close()