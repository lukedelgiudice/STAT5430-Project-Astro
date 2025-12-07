import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import MiniBatchKMeans, AgglomerativeClustering
from config import OUTPUT_DIR

def run(data):
    all_deaths = []
    for d in data:
        if 'S4' in d:
            all_deaths.extend(d['S4'])
    
    if all_deaths:
        df_deaths = pd.DataFrame(all_deaths)
        os.makedirs(f"{OUTPUT_DIR}/spatial", exist_ok=True)
        df_deaths.to_csv(f"{OUTPUT_DIR}/spatial/s5_deaths_raw.csv", index=False)

        for map_name in df_deaths['map'].unique():            
            map_data = df_deaths[df_deaths['map'] == map_name].copy()
            coords = map_data[['x', 'y', 'z']].values
            
            if len(coords) < 10:
                continue

            try:
                n_micro_clusters = max(1, int(len(coords) / 5))
                
                init_size = max(3 * n_micro_clusters, 100)
                if init_size > len(coords): init_size = len(coords)

                kmeans = MiniBatchKMeans(
                    n_clusters=n_micro_clusters, 
                    batch_size=256, 
                    random_state=42, 
                    n_init=3,
                    init_size=init_size
                )
                kmeans.fit(coords)
                
                micro_centers = kmeans.cluster_centers_ 
                
                unique_labels, counts = np.unique(kmeans.labels_, return_counts=True)
                weight_map = dict(zip(unique_labels, counts))
                
                micro_weights = np.array([weight_map.get(i, 0) for i in range(len(micro_centers))])
                
                df_micro = pd.DataFrame(micro_centers, columns=['x', 'y', 'z'])
                df_micro['weight'] = micro_weights
                
                df_micro = df_micro[df_micro['weight'] > 0].copy().reset_index(drop=True)
                
                MERGE_DIST = 300.0 
                
                agg = AgglomerativeClustering(
                    n_clusters=None, 
                    distance_threshold=MERGE_DIST, 
                    linkage='average',
                    metric='euclidean'
                )
                
                agg_labels = agg.fit_predict(df_micro[['x', 'y', 'z']].values)
                
                df_micro['label'] = agg_labels
                
                final_clusters = []
                
                for label, group in df_micro.groupby('label'):
                    total_weight = group['weight'].sum()
                    
                    avg_x = np.average(group['x'], weights=group['weight'])
                    avg_y = np.average(group['y'], weights=group['weight'])
                    avg_z = np.average(group['z'], weights=group['weight'])
                    
                    final_clusters.append({'x': avg_x, 'y': avg_y, 'z': avg_z, 'count': int(total_weight)})
                
                df_final = pd.DataFrame(final_clusters)
                
                cluster_filename = f"{OUTPUT_DIR}/spatial/s5_clusters_{map_name}.csv"
                df_final.to_csv(cluster_filename, index=False)

                plt.figure(figsize=(10,10))
                sns.kdeplot(x=map_data['x'], y=map_data['y'], cmap="inferno", fill=True, thresh=0.05, alpha=0.8)
                plt.title(f"s5: Death Density Top-Down ({map_name})")
                plt.axis('equal')
                plt.savefig(f"{OUTPUT_DIR}/graphs/s5_heatmap_{map_name}.png")
                plt.close()

            except Exception as e:
                print(f"clustering failed for {map_name}: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("skipping s5 (no death locations or missing sklearn libraries)")
