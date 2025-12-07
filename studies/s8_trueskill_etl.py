from studies.s1_summary_etl import extract as s1_extract

def extract(processor):
    s1_data = s1_extract(processor)
    return s1_data['players']