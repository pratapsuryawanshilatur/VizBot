# It handles packaging of graphs and insights, and save graph images to local so users can download them.
import plotly.io as pio # to export Plotly figures as images.
import os
import uuid # Generate unique ids so file names don't clash.
from typing import Dict, Any
import plotly.graph_objects as go

class OutputAgent:
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        output = {
            "graph_outputs": [],
            "insights": input_data.get("insights", "")
        } # building return object, so it collect insights and initialize empty graph list.

        graph_outputs = input_data.get("graphs", {}).get("graph_outputs", [])
        for graph_info in graph_outputs:
            fig = graph_info.get("fig")
            title = graph_info.get("title", "Graph")
            # Check that fig is valid Plotly figure before trying to save it.
            if isinstance(fig, go.Figure):
                # Generate unique filename with title + short uuid.
                graph_id = str(uuid.uuid4())[:8]
                graph_path = f"data/graph_images/{title.replace(' ', '_')}_{graph_id}.png"
                os.makedirs(os.path.dirname(graph_path), exist_ok=True)
                try:
                    pio.write_image(fig, graph_path, format="png")
                    graph_info["download_link"] = graph_path
                except Exception as e:
                    graph_info["note"] = f"Failed to save image: {e}"
            output["graph_outputs"].append(graph_info)

        print("[DEBUG] OutputAgent processed graphs:", output["graph_outputs"])
        return output # Print for dev visibility 
