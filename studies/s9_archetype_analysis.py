import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import os
from config import OUTPUT_DIR

def run(data):
    user_profiles = defaultdict(list)
    for d in data:
        for u, prof in d['S9'].items():
            user_profiles[u].append(prof)
    
    final_profs = []
    for u, profs in user_profiles.items():
        if not profs:
            continue
        avg = {'Username': u}
        for k in profs[0].keys():
            avg[k] = np.mean([p[k] for p in profs])
        final_profs.append(avg)
        
    df_prof = pd.DataFrame(final_profs)
    if not df_prof.empty:
        df_prof.to_csv(os.path.join(OUTPUT_DIR, "data", "s9_playstyles.csv"), index=False)
        
        if len(df_prof) > 3:
            features = df_prof.drop('Username', axis=1)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(features)
            
            kmeans = KMeans(n_clusters=3, random_state=42).fit(X_scaled)
            df_prof['Cluster'] = kmeans.labels_
            
            pd.DataFrame(kmeans.cluster_centers_, columns=features.columns).to_csv(os.path.join(OUTPUT_DIR, "data", "s9_cluster_centers.csv"))
            
            sns.pairplot(df_prof, hue='Cluster', palette='viridis')
            plt.savefig(os.path.join(OUTPUT_DIR, "graphs", "s9_archetypes_pairplot.png"))
            plt.close()