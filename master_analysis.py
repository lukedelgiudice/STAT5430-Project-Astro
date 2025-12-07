import glob
import os
import time
import importlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import matplotlib

from config import OUTPUT_DIR, SUBDIRS, USE_SINGLE_CORE

from game_etl import process_single_file

from studies import (
    s0_metadata_analysis,
    s1_summary_analysis,
    s2_health_analysis,
    s3_winrate_analysis,
    s4_spatial_analysis,
    s5_sequence_analysis,
    s6_velocity_analysis,
    s7_survival_analysis,
    s8_trueskill_analysis,
    s9_archetype_analysis,
    s10_performance_analysis
)

STUDY_MODULES = [
    s0_metadata_analysis,
    s1_summary_analysis,
    s2_health_analysis,
    s3_winrate_analysis,
    s4_spatial_analysis,
    s5_sequence_analysis,
    s6_velocity_analysis,
    s7_survival_analysis,
    s8_trueskill_analysis,
    s9_archetype_analysis,
    s10_performance_analysis
]

def setup_directories():
    for sd in SUBDIRS:
        os.makedirs(os.path.join(OUTPUT_DIR, sd), exist_ok=True)
    #print(f"created output directories in {OUTPUT_DIR}/")

def run_study_wrapper(module_name, data):
    try:
        import matplotlib
        matplotlib.use('Agg')
        
        module = importlib.import_module(module_name)
        
        name = module_name.split('.')[-1]
        start = time.perf_counter()
        module.run(data)
        duration = time.perf_counter() - start
        return f"✔ {name} completed in {duration:.2f}s"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"✘ {module_name} FAILED: {e}"

def main(data_folder="."):
    total_start_time = time.perf_counter()
    setup_directories()

    print(f"1) discovering game files in '{data_folder}'")
    
    json_files = glob.glob(os.path.join(data_folder, "Match_*.json")) 
    tasks = []
    
    for j_path in json_files:
        try:
            filename = os.path.basename(j_path)
            parts = filename.split('_')
            if len(parts) > 1:
                game_id = parts[1].replace('.json', '')
            else:
                continue

            u_path = os.path.join(data_folder, f"PlayerUpdate_{game_id}.csv")
            p_paths = glob.glob(os.path.join(data_folder, f"Performance_*_{game_id}.csv"))
            
            if os.path.exists(u_path):
                tasks.append((game_id, j_path, u_path, p_paths))
        except Exception as e:
            print(f"skipping {j_path}: {e}")
            continue

    #print(f"found {len(tasks)} valid games to process.")

    # 2) data extraction
    print(f"\n2) starting extraction ({'SINGLE' if USE_SINGLE_CORE else 'MULTI'}-CORE)")
    extract_start = time.perf_counter()
    extracted_data = []

    if USE_SINGLE_CORE:
        for i, task in enumerate(tasks):
            try:
                res = process_single_file(task)
                if res:
                    extracted_data.append(res)
                if (i + 1) % 10 == 0:
                    print(f"  extracted {i + 1}/{len(tasks)}")
            except Exception as e:
                print(f"  failed {task[0]}: {e}")
    else:
        with ProcessPoolExecutor() as pool:
            results = pool.map(process_single_file, tasks)
            for i, res in enumerate(results):
                if res:
                    extracted_data.append(res)
                if (i + 1) % 10 == 0:
                    print(f"  extracted {i + 1}/{len(tasks)}")

    extract_duration = time.perf_counter() - extract_start
    print(f"  extraction complete ({len(extracted_data)}/{len(tasks)} games)")
    print(f"  Time: {extract_duration/60:.2f}m")

    if not extracted_data:
        print("no data extracted")
        return

    # 2) output/analysis
    print(f"\n3) starting analysis ({'SINGLE' if USE_SINGLE_CORE else 'MULTI'}-CORE) ---")
    analysis_start = time.perf_counter()

    if USE_SINGLE_CORE:
        for mod in STUDY_MODULES:
            try:
                print(f"running {mod.__name__}...")
                mod.run(extracted_data)
            except Exception as e:
                print(f"error in {mod.__name__}: {e}")
    else:
        with ProcessPoolExecutor() as pool:
            futures = {
                pool.submit(run_study_wrapper, mod.__name__, extracted_data): mod.__name__
                for mod in STUDY_MODULES
            }
            
            for future in as_completed(futures):
                result_msg = future.result()
                print(f"  {result_msg}")

    analysis_duration = time.perf_counter() - analysis_start
    total_duration = time.perf_counter() - total_start_time

    print("\n" + "="*40)
    print(" pipeline complete")
    print("="*40)
    print(f" extraction time: {int(extract_duration // 60)}m {int(extract_duration % 60)}s")
    print(f" analysis time:   {int(analysis_duration // 60)}m {int(analysis_duration % 60)}s")
    print(f" total runtime:   {int(total_duration // 60)}m {int(total_duration % 60)}s")
    print(f" output location: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    matplotlib.use('Agg') 
    
    main(data_folder="match_data")