"""Explicit chart colours, independent of Plotly's global defaults."""
from itertools import cycle


def apply_colors(fig, palette, mode='Palette', single=None, overrides=None):
    overrides = overrides or {}
    single = single or palette[0]
    scale = [[0, palette[0]], [.5, '#f2f5ef'], [1, palette[1]]]
    fig.update_layout(colorway=palette)
    for i, trace in enumerate(fig.data):
        c = single if mode == 'Single colour' else palette[i % len(palette)]
        if trace.type == 'heatmap':
            trace.update(colorscale=scale)
            continue
        if trace.type == 'bar':
            axis = trace.y if trace.orientation == 'h' else trace.x
            if mode != 'Single colour' and axis is not None:
                mapping = dict(zip(dict.fromkeys(str(v) for v in axis), cycle(palette)))
                trace.marker.color = [overrides.get(str(v), mapping[str(v)]) if mode == 'Individual colours' else (c if len(fig.data)>1 else mapping[str(v)]) for v in axis]
            else:
                trace.marker.color = c
        elif trace.type in ('scatter', 'scattergl', 'histogram', 'box', 'violin'):
            marker = trace.marker
            # Preserve numeric colour encodings and their colourbar.
            if not getattr(marker, 'coloraxis', None) and not (getattr(marker, 'color', None) is not None and not isinstance(marker.color, str)):
                marker.color = c
            if hasattr(trace, 'line'):
                trace.line.color = c
        elif trace.type == 'pie':
            trace.marker.colors = [single if mode == 'Single colour' else overrides.get(str(v), palette[j % len(palette)]) for j,v in enumerate(trace.labels)]
    if fig.layout.coloraxis.colorscale is not None or any(t.type == 'heatmap' for t in fig.data):
        fig.update_coloraxes(colorscale=scale)
    return fig
