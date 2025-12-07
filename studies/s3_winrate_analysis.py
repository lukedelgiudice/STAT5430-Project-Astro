import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
import os
from config import OUTPUT_DIR

def run(data):
    all_s3 = []
    for d in data: 
        if 'S3' in d:
            all_s3.extend(d['S3'])
            
    df_glmm = pd.DataFrame(all_s3)
    
    if not df_glmm.empty:
        df_glmm.to_csv(os.path.join(OUTPUT_DIR, "data", "s3_glmm_input.csv"), index=False)
        
        try:
            df_glmm['start_dist_scaled'] = df_glmm['start_dist'] / 1000.0
            
            item_counts = df_glmm['item_used'].value_counts()
            valid_items = item_counts[item_counts >= 5].index
            df_clean = df_glmm[df_glmm['item_used'].isin(valid_items)].copy()
            
            if df_clean.empty:
                # not enough data after filtering
                return

            mod = smf.glm(
                "win ~ C(item_used) + start_dist_scaled + start_health", 
                data=df_clean, 
                family=sm.families.Binomial(), 
                freq_weights=df_clean['attribution_weight']
            ).fit()
            
            with open(os.path.join(OUTPUT_DIR, "models", "s3_glmm_summary.txt"), "w") as f:
                f.write(mod.summary().as_text())
            
            params = mod.params
            conf = mod.conf_int()
            conf['OR'] = np.exp(params)
            conf.columns = ['Lower CI', 'Upper CI', 'OR']
            
            item_rows = conf[conf.index.str.contains("item_used")]
            
            if not item_rows.empty:
                item_rows.index = item_rows.index.str.replace(r"C\(item_used\)\[T\.(.*?)\]", r"\1", regex=True)
                item_rows = item_rows.sort_values('OR', ascending=True)
                
                plt.figure(figsize=(10, max(6, len(item_rows) * 0.5)))
                
                for i, (idx, row) in enumerate(item_rows.iterrows()):
                    color = 'grey'
                    if row['Lower CI'] > 1: color = 'green'
                    elif row['Upper CI'] < 1: color = 'red'
                    
                    plt.plot(row['OR'], i, 'o', color=color, markersize=10, alpha=0.9)
                    
                    plt.text(row['OR'], i + 0.15, f"{row['OR']:.2f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

                plt.yticks(range(len(item_rows)), item_rows.index)
                plt.axvline(1, color='black', linestyle='--', linewidth=1, alpha=0.5)
                plt.title("s3: Item Win Probability (Odds Ratios)")
                plt.xlabel("Odds Ratio (Log Scale)")
                plt.xscale('log')
                plt.xticks([0.5, 1, 2, 5], ['0.5x', '1.0x', '2.0x', '5.0x'])
                plt.grid(True, axis='x', which='both', linestyle=':', alpha=0.3)
                plt.tight_layout()
                plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s3_winrate_forest.png"))
                plt.close()
            else:
                print("no item coefficients found.")

        except Exception as e:
            print(f"s3 glm failed: {e}")
            with open(os.path.join(OUTPUT_DIR, "models", "s3_error.txt"), "w") as f:
                f.write(str(e))
    else:
        print("skipping s3 (no valid fight data found)")