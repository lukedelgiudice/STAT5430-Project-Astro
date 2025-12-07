def extract(processor):
    s1_perf = {} 
    
    for username, df in processor.perf_dfs.items():
        if df is None or df.empty: continue
        
        p_stats = {
            'gpu_bound_frames': 0, 
            'nettick_bound_frames': 0, 
            'gt_bound_frames': 0,
            'total_frames': len(df), 
            'avg_latency': 0, 
            'avg_fps': 0
        }
        
        if 'GPU Bound' in df.columns: p_stats['gpu_bound_frames'] = int(df['GPU Bound'].sum())
        if 'GT Bound' in df.columns: p_stats['gt_bound_frames'] = int(df['GT Bound'].sum())
        if 'NTT Bound' in df.columns: p_stats['nettick_bound_frames'] = int(df['NTT Bound'].sum())
        
        if 'Packet Latency' in df.columns:
            p_stats['avg_latency'] = float(df['Packet Latency'].mean())
            p_stats['all_latencies'] = df['Packet Latency'].astype(float).tolist()
            
        if 'Frame Avg' in df.columns:
            avg_frame_ms = df['Frame Avg'].mean()
            p_stats['avg_fps'] = 1000.0 / avg_frame_ms if avg_frame_ms > 0 else 0

        s1_perf[username] = p_stats
        
    return s1_perf