import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import warnings
import os
from config import OUTPUT_DIR

def run(data):
    all_S6 = []
    for d in data: 
        if 'S6' in d: all_S6.extend(d['S6'])
    
    if all_S6:
        max_len = max(len(x['curve']) for x in all_S6)
        time_axis = np.linspace(-max_len / 2.0, 0, max_len)

        kills_data = [x['curve'] for x in all_S6 if x['result'] == 'kill']
        deaths_data = [x['curve'] for x in all_S6 if x['result'] == 'death']
        
        def get_curve_stats(curves, target_len):
            if not curves: 
                return np.full(target_len, np.nan), np.full(target_len, np.nan)
            
            mat = np.full((len(curves), target_len), np.nan)
            
            for i, c in enumerate(curves):
                segment = c[-target_len:] 
                mat[i, -len(segment):] = segment
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                mu = np.nanmean(mat, axis=0)
                sigma = np.nanstd(mat, axis=0)
                
            return mu, sigma

        mean_kill, std_kill = get_curve_stats(kills_data, max_len)
        mean_death, std_death = get_curve_stats(deaths_data, max_len)
        
        coeffs = []
        
        X_full = np.full((len(all_S6), max_len), np.nan)
        y_full = np.array([1 if x['result'] == 'kill' else 0 for x in all_S6])
        
        for i, entry in enumerate(all_S6):
            c = entry['curve']
            X_full[i, -len(c):] = c[-max_len:]

        for t in range(max_len):
            col = X_full[:, t]
            mask = ~np.isnan(col)
            X_t = col[mask]
            y_t = y_full[mask]
            
            if len(X_t) > 20 and np.std(X_t) > 0 and len(np.unique(y_t)) > 1:
                try:
                    model = sm.Logit(y_t, sm.add_constant(X_t)).fit(disp=0)
                    coeffs.append(model.params[1])
                except:
                    coeffs.append(np.nan)
            else:
                coeffs.append(np.nan)

        df_curve = pd.DataFrame({
            'Time_Before_Event': time_axis,
            'Mean_Velocity_Killer': mean_kill,
            'Mean_Velocity_Victim': mean_death,
            'Logit_Coefficient': coeffs
        })
        df_curve.to_csv(os.path.join(OUTPUT_DIR, "data", "s6_velocity_curve.csv"), index=False)
        
        plt.figure(figsize=(10, 6))
        if not np.all(np.isnan(mean_kill)):
            plt.plot(time_axis, mean_kill, color='blue', label='Killers (Win)')
            plt.fill_between(time_axis, mean_kill - std_kill, mean_kill + std_kill, color='blue', alpha=0.1)
        
        if not np.all(np.isnan(mean_death)):
            plt.plot(time_axis, mean_death, color='red', label='Victims (Loss)')
            plt.fill_between(time_axis, mean_death - std_death, mean_death + std_death, color='red', alpha=0.1)
            
        plt.title("Average Velocity Before Outcome")
        plt.xlabel("Seconds Before Event")
        plt.ylabel("Velocity (Units/s)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s6_velocity_curve.png"))
        plt.close()

        if not np.all(np.isnan(coeffs)):
            plt.figure(figsize=(10, 6))
            coeffs_smooth = pd.Series(coeffs).rolling(5, center=True, min_periods=1).mean()
            
            plt.plot(time_axis, coeffs_smooth, color='purple', linewidth=2)
            plt.axhline(0, color='black', linestyle='--', linewidth=1)
            
            plt.title("Logistic Coefficients")
            plt.xlabel("Seconds Before Event")
            plt.ylabel("Coefficient (Positive = Speed Helps)")
            
            plt.text(time_axis[-1], max(coeffs_smooth)*0.8, " Speed helps Win", color='green', ha='right')
            plt.text(time_axis[-1], min(coeffs_smooth)*0.8, " Speed causes Loss", color='red', ha='right')
            
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s6_velocity_coefficients.png"))
            plt.close()
            
    else:
        print("s6 skipped (no velocity curves found)")