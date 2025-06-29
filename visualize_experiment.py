asc_file = input("Enter the path to the ASC file: ")

from stimulus.Mot.visualize_mot import visualize_mot_experiment
from parser import AscParser
from stimulus.VisualSearch.VisualSearchVisualization import visual_search_visualization
# ------------------------------------------------------------------
# Optional CLI helper for quick inspection
# ------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json


    asc = AscParser(asc_file)
    print(json.dumps(asc.summary(), indent=2))
   
    visualize_mot_experiment(asc)
    #visual_search_visualization(asc)