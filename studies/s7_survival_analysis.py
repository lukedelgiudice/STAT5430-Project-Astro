import pandas as pd
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from config import OUTPUT_DIR

def run(data):
    all_fights = []
    for d in data: 
        if 'S7' in d:
            all_fights.extend(d['S7'])
            
    df_surv = pd.DataFrame(all_fights)
    
    if not df_surv.empty:
        df_surv.to_csv(f"{OUTPUT_DIR}/data/s7_fights_processed.csv", index=False)
        
        kmf = KaplanMeierFitter()
        
        T = df_surv['duration']
        E = [1]*len(T)
        
        plt.figure(figsize=(10,6))
        kmf.fit(T, event_observed=E, label="All Fights")
        kmf.plot_survival_function(ci_show=True)
        
        median_dur = kmf.median_survival_time_
        plt.axvline(median_dur, color='b', linestyle='--', label=f"Median Duration: {median_dur:.2f}s")
        
        plt.title("Fight Duration Survival Curve (All Outcomes)")
        plt.xlabel("Time in Fight (seconds)")
        plt.ylabel("Probability of Engagement Continuing")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{OUTPUT_DIR}/graphs/s7_fight_duration_all.png")
        plt.close()
        
        if 'end_reason' in df_surv.columns:
            df_death = df_surv[df_surv['end_reason'] == 'death']
            
            if not df_death.empty:
                T_d = df_death['duration']
                E_d = [1]*len(T_d)
                
                plt.figure(figsize=(10,6))
                kmf.fit(T_d, event_observed=E_d, label="Fatal Fights Only")
                kmf.plot_survival_function(ci_show=True, color='crimson')
                
                median_ttk = kmf.median_survival_time_
                plt.axvline(median_ttk, color='k', linestyle='--', label=f"Median TTK: {median_ttk:.2f}s")
                
                plt.title("Time-To-Kill Survival Curve (Deaths Only)")
                plt.xlabel("Time until Death (seconds)")
                plt.ylabel("Probability of Survival")
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.savefig(f"{OUTPUT_DIR}/graphs/s7_ttk_curve_deaths.png")
                plt.close()
            else:
                print("no fatal fights found for s7")
        else:
            print("'end_reason' column missing in fight data")
