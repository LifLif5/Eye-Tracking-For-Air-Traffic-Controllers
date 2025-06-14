from stimulus.Mot.visualize_mot import visualize_mot_experiment
from parser import AscParser
from stimulus.VisualSearch.VisualSearchVisualization import visual_search_visualization
# ------------------------------------------------------------------
# Optional CLI helper for quick inspection
# ------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(
        description="Parse EDF2ASC .asc eye‑tracking file and print a summary."
    )
    parser.add_argument("asc_file", help="Path to .asc file")
    args = parser.parse_args()

    asc = AscParser(args.asc_file)
    print(json.dumps(asc.summary(), indent=2))
   
    # visualize_mot_experiment(asc)
    visual_search_visualization(asc)