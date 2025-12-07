import traceback
from game_etl_core import GameProcessor

from studies import (
    s0_metadata_etl,
    s1_summary_etl,
    s2_health_etl,
    s3_winrate_etl,
    s4_spatial_etl,
    s5_sequence_etl,
    s6_velocity_etl,
    s7_survival_etl,
    s8_trueskill_etl,
    s9_archetype_etl,
    s10_performance_etl,
    s11_niche_etl,
    s12_path_etl,
    s13_idle_etl
)

def process_single_file(file_group):
    gid, j_path, u_path, p_paths_list = file_group
    
    try:
        processor = GameProcessor(gid, j_path, u_path, p_paths_list)
        
        results = {}
        
        results['S0'] = s0_metadata_etl.extract(processor)
        results['S1'] = s1_summary_etl.extract(processor)
        results['S2'] = s2_health_etl.extract(processor)
        results['S3'] = s3_winrate_etl.extract(processor)
        results['S4'] = s4_spatial_etl.extract(processor)
        results['S5'] = s5_sequence_etl.extract(processor)
        results['S6'] = s6_velocity_etl.extract(processor)
        results['S7'] = s7_survival_etl.extract(processor)
        results['S8'] = s8_trueskill_etl.extract(processor)
        results['S9'] = s9_archetype_etl.extract(processor)
        results['S10'] = s10_performance_etl.extract(processor)
        results['S11'] = s11_niche_etl.extract(processor)
        results['S12'] = s12_path_etl.extract(processor)
        results['S13'] = s13_idle_etl.extract(processor)

        return results

    except Exception as e:
        print(f"failed {gid}: {e}")
        traceback.print_exc()
        return None