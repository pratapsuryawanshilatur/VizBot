# To take cleaned data from preprocessor and generate the requested graph type using Plotly.
import pandas as pd
import plotly.graph_objects as go # allows us to create graphs
import plotly.express as px # provides access to color palettes.
from typing import Dict, Any

class GraphGenerator:
    # Takes the processed data, requested graph type, and returns a packaged graph output.
    def run(self, processed_data: Dict[str, Any], graph_type: str = "line") -> Dict[str, Any]:
        df = processed_data.get("df")
        download_link = processed_data.get("download_link", "") # Extract the dataframe and download link if provided by preprocessor.
        filters = processed_data.get("filters", {})

        if df is None or df.empty:
            fig = self._empty_figure("No data available for this query.")
            return self._package_output(fig, "No Data", download_link) # Early exit-if no data, return blank graph.

        print(f"[DEBUG] Graph type requested: {graph_type}")

        graph_type_func_map = {
            "line": self._generate_line_plot,
            "bar": self._generate_bar_plot,
            "heatmap": self._generate_heatmap,
            "box": self._generate_box_plot
        } # This maps graph type names to other functions.

        plot_func = graph_type_func_map.get(graph_type, self._generate_line_plot)
        fig, title = plot_func(df, filters) # pick the graph type requested, default to line plot if unknown.

        if not fig or not isinstance(fig, go.Figure):
            print("[DEBUG] Generated fig is invalid. Returning empty placeholder.")
            fig = self._empty_figure("Graph could not be generated.")
            title = "Empty Graph"

        return self._package_output(fig, title, download_link) # packs into a dict for the output agent.

    def _package_output(self, fig, title, download_link):
        return {
            "graph_outputs": [{
                "title": title,
                "fig": fig,
                "download_link": download_link
            }]
        } # packages output in consistent dict format.

    def _empty_figure(self, message):
        fig = go.Figure()
        fig.add_annotation(text=message, showarrow=False)
        return fig # creates a blank figure with a centered message for no data cases.

    def _get_colors(self):
        # Automatically use a rich qualitative palette
        return px.colors.qualitative.Alphabet # provides a wide set of distinct colors so multiple rooms look visually distinct.

    def _generate_line_plot(self, df: pd.DataFrame, filters=None):
        fig = go.Figure()
        colors = self._get_colors()
        markers = ['circle', 'square', 'diamond', 'cross', 'x', 'star']

        if "Room_Name" not in df.columns:
            return self._empty_figure("Line plot requires Room_Name column.")

        if "start_time" not in df.columns:
            return self._empty_figure("Line plot requires time-series data. Try a bar or box plot instead.")

        group_cols = ["Room_Name", "geometry_id"]
        if "metric_name" in df.columns and df["metric_name"].nunique() > 1:
            group_cols.append("metric_name")

        unique_groups = df.groupby(group_cols).size().reset_index().drop(0, axis=1)

        agg_method = "mean"
        if filters and isinstance(filters, dict):
            user_agg = str(filters.get("aggregation", "")).lower()
            if "max" in user_agg:
                agg_method = "max"
            elif "min" in user_agg:
                agg_method = "min"

        for i, row in unique_groups.iterrows():
            group_filter = (df["Room_Name"] == row["Room_Name"]) & (df["geometry_id"] == row["geometry_id"])
            name = f"{row['Room_Name']} ({row['geometry_id']})"

            if "metric_name" in row:
                group_filter &= df["metric_name"] == row["metric_name"]
                name += f" - {row['metric_name']}"

            room_data = df[group_filter]

            # Aggregate to one point per timestamp to avoid overlapping lines
            room_data_agg = (
                room_data.groupby("start_time", as_index=False)
                .agg({"value": agg_method})
                .sort_values("start_time")
            )

            fig.add_trace(go.Scatter(
                x=room_data_agg["start_time"],
                y=room_data_agg["value"],
                mode="lines+markers",
                name=name,
                line=dict(color=colors[i % len(colors)], width=2, shape="spline"),
                marker=dict(symbol=markers[i % len(markers)], size=4)
            ))

        metric = ", ".join(filters.get("metric_name", [])).upper() if filters else "Metric"

        fig.update_layout(
            title=f"{metric} Over Time",
            xaxis_title="Time",
            yaxis_title="metric",
            legend_title="Room/Metric",
            hovermode="x unified"
        )
        return fig, f"{metric} Over Time"

    def _generate_bar_plot(self, df: pd.DataFrame, filters=None):
        if "Room_Name" not in df.columns:
            return self._empty_figure("Bar plot requires Room_Name column."), "Missing Columns"

        group_cols = ["Room_Name", "geometry_id"]
        if "metric_name" in df.columns and df["metric_name"].nunique() > 1:
            group_cols.append("metric_name")

        # If continuous_high_count exists, use it for bar height
        use_continuous = "continuous_high_count" in df.columns
        agg_col = "continuous_high_count" if use_continuous else "value"
        y_label = "Continuous High Count" if use_continuous else "Avg Value"
        title = "Rooms with Continuous High Values" if use_continuous else "Average Metrics by Room"

        grouped = df.groupby(group_cols)[agg_col].mean().reset_index()
        if grouped.empty:
            return self._empty_figure("No data for Bar plot.")

        fig = go.Figure()
        colors = self._get_colors()

        for i, row in grouped.iterrows():
            name = f"{row['Room_Name']} ({row['geometry_id']})"
            if "metric_name" in row:
                name += f" - {row['metric_name']}"
            fig.add_trace(go.Bar(
                x=[name],
                y=[row[agg_col]],
                name=name,
                marker_color=colors[i % len(colors)]
            ))

        metric = ", ".join(filters.get("metric_name", [])).upper() if filters else "Metric"
        agg = filters.get("aggregation", "").upper() if filters else ""
        graph_title = f"{agg} {metric} by Room" if agg and not use_continuous else title

        fig.update_layout(
            title=graph_title,
            xaxis_title="Room / Metric",
            yaxis_title=y_label,
            legend_title="Room/Metric"
        )
        return fig, graph_title

    def _generate_heatmap(self, df: pd.DataFrame, filters=None):
        if "hour" not in df.columns or "dayofweek" not in df.columns:
            return self._empty_figure("Heatmap requires 'hour' and 'dayofweek' columns."), "Missing Columns"

        # If multiple metrics, warn the user (heatmap cannot show all at once)
        if "metric_name" in df.columns and df["metric_name"].nunique() > 1:
            return self._empty_figure("Heatmap currently supports one metric at a time. Please filter your query."), "Invalid Metric Set"

        grouped = df.groupby(["dayofweek", "hour"])["value"].mean().reset_index()
        pivot = grouped.pivot(index="dayofweek", columns="hour", values="value")

        if pivot.empty:
            return self._empty_figure("No data for Heatmap."), "Empty Heatmap"
        
        metric = ", ".join(filters.get("metric_name", [])).upper() if filters else "Metric"

        fig = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Viridis",
            colorbar_title="metric"
        ))

        fig.update_layout(
            title=f"{metric} Heatmap (Day vs Hour)",
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week"
        )
        return fig, f"{metric} Heatmap (Day vs Hour)"

    def _generate_box_plot(self, df: pd.DataFrame, filters=None):
        if "Room_Name" not in df.columns:
            return self._empty_figure("Box plot requires Room_Name column."), "Missing Columns"

        fig = go.Figure()
        colors = self._get_colors()

        group_cols = ["Room_Name", "geometry_id"]
        if "metric_name" in df.columns and df["metric_name"].nunique() > 1:
            group_cols.append("metric_name")

        unique_groups = df.groupby(group_cols).size().reset_index().drop(0, axis=1)

        for i, row in unique_groups.iterrows():
            group_filter = (df["Room_Name"] == row["Room_Name"]) & (df["geometry_id"] == row["geometry_id"])
            name = f"{row['Room_Name']} ({row['geometry_id']})"

            if "metric_name" in row:
                group_filter &= df["metric_name"] == row["metric_name"]
                name += f" - {row['metric_name']}"

            room_data = df[group_filter]
            fig.add_trace(go.Box(
                y=room_data["value"],
                name=name,
                marker_color=colors[i % len(colors)]
            ))
        
        metric = ", ".join(filters.get("metric_name", [])).upper() if filters else "Metric"

        fig.update_layout(
            title=f"{metric} Distribution by Room",
            yaxis_title="Value",
            legend_title="Room/Metric"
        )
        return fig, f"{metric} Distribution by Room"


