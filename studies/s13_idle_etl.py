def extract(processor):
    s14_idle_times = []
    for f in processor.fights:
        s14_idle_times.extend(list(f['idle_pre'].values()))
    return s14_idle_times