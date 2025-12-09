# Game Data Analytics Pipeline

Author: **Luke Del Giudice**

This repository contains a modular Python pipeline designed to extract and analyze data from the game Astro.

The presentation google slideshow link: https://docs.google.com/presentation/d/1a9XUK3Q5WCbq289itJT7fzWBEtFkoV1gci7Adz-uIeI/edit?usp=sharing

## :snake: Python Dependencies

Install the required libraries using pip (or any other package installer):

pip install pandas numpy matplotlib seaborn scikit-learn statsmodels lifelines squarify trueskill scipy

## :file_folder: Repository Structure

* `master_analysis.py`: the entry point of the pipeline
* `game_etl.py`: controls the extraction phase, delegating tasks to specific study ETL scripts
* `game_etl_core.py`: parses the JSON event files to establish player states/identities and detect fights

* `config.py`: contains global constants and configuration flags
* `studies/`: a package containing paired etl (_etl.py) and analysis (_analysis.py) scripts for each study
* `blender_scripts/`: Python scripts to be run inside Blender for s4
* `match_data/`: a folder containing all of the gameplay data used in this analysis

* `ReplayDriver_GameStats`: the C++ script used for initial data aggregation in the executable (not runnable, just for review purposes)

# :rocket: How to Run

Run the master script `master_analysis.py` from the root directory

The terminal will display progress bars for the extraction phase followed by the analysis phase. Upon completion, a summary of runtimes will be displayed.

# :bar_chart: Outputs

All results are generated in the `results/` folder, organized by type:

* `results/data/`: raw CSVs containing processed statistics
* `results/graphs/`: visualizations (ie: s3_winrate_forest.png)
* `results/spatial/`: centroid data for 3D mapping (ie: s5_clusters_MapName.csv)
* `results/models/`: text summaries of statistical models (s3_glm_summary.txt)

# :earth_americas: Visualizing Spatial Data (Study 4)

Study 4 produces 3D clustering data that requires external tools to visualize. Since you don't have access to the actual map fbx files, I imported one of the maps into an fbx for visualzation (unfortunately, its transform seems to be off). To recreate the spheres themselves, open `import_death_clusters.py` in the Scripting tab of Blender and edit the *CSV_PATH* variable in the script to point to the absolute path of the generated csv. After running this script, open `death_cluster_exporter.py` and edit its *EXPORT_PATH* to where you want the fbx file saved. Run the script. This bakes the data into Vertex Colors and exports the mesh.

# :question: Questions

Please reach out with any questions!