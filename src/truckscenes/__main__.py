#!/usr/bin/env python3
"""
TruckScenes DevKit CLI

Usage:
    python -m truckscenes                         # Normal visualization
    python -m truckscenes --foxglove              # Stream to Foxglove Studio
    python -m truckscenes --foxglove --port 9090  # Custom port
    python -m truckscenes --scene 0               # Render specific scene
"""

import argparse
import os
import sys

from truckscenes import TruckScenes
from truckscenes.utils.visualization_utils import TruckScenesExplorer


def run_visualization(ts: TruckScenes, args):
    """Run standard TruckScenes visualization using TruckScenesExplorer."""
    explorer = TruckScenesExplorer(ts)
    
    if args.sample:
        print(f"Rendering sample: {args.sample}")
        explorer.render_sample(args.sample)
    elif args.scene is not None:
        if args.scene < len(ts.scene):
            scene_token = ts.scene[args.scene]['token']
            print(f"Rendering scene {args.scene}: {scene_token}")
            explorer.render_scene(scene_token)
        else:
            print(f"Error: Scene index {args.scene} out of range (0-{len(ts.scene)-1})")
            sys.exit(1)
    else:
        # Default: render first scene
        if ts.scene:
            scene_token = ts.scene[0]['token']
            print(f"Rendering first scene: {scene_token}")
            explorer.render_scene(scene_token)
        else:
            print("No scenes available!")
            sys.exit(1)


def run_foxglove(ts: TruckScenes, args):
    """Run Foxglove streaming mode."""
    try:
        from truckscenes.foxglove_streamer import FoxgloveStreamer
    except ImportError as e:
        print("Error: foxglove-websocket not installed.")
        print("Install with: pip install foxglove-websocket")
        sys.exit(1)
    
    print(f"Starting Foxglove WebSocket server on port {args.port}...")
    print(f"Connect Foxglove Studio to ws://localhost:{args.port}")
    streamer = FoxgloveStreamer(ts, port=args.port)
    streamer.run()


def main():
    parser = argparse.ArgumentParser(
        description="TruckScenes DevKit - Visualization and Foxglove Streaming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m truckscenes                    # Normal visualization (first scene)
  python -m truckscenes --scene 2          # Render scene at index 2
  python -m truckscenes --foxglove         # Stream to Foxglove Studio
  python -m truckscenes --foxglove --port 9090
        """
    )
    
    # Mode selection
    parser.add_argument(
        "--foxglove", action="store_true",
        help="Stream data to Foxglove Studio via WebSocket instead of visualization"
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Foxglove WebSocket port (default: 8765)"
    )
    
    # Visualization options
    parser.add_argument(
        "--scene", type=int, default=None,
        help="Scene index to render (default: 0)"
    )
    parser.add_argument(
        "--sample", type=str, default=None,
        help="Sample token to render"
    )
    
    # Data options
    parser.add_argument(
        "--dataroot", type=str,
        default=os.getenv("TRUCKSCENES_DATAROOT", "../data/man-truckscenes"),
        help="Path to TruckScenes data (default: ../data/man-truckscenes)"
    )
    parser.add_argument(
        "--version", type=str,
        default=os.getenv("TRUCKSCENES_VERSION", "v1.1-mini"),
        help="TruckScenes version (default: v1.1-mini)"
    )
    
    args = parser.parse_args()
    
    # Validate dataroot
    if not os.path.exists(args.dataroot):
        print(f"Error: Data directory not found: {args.dataroot}")
        print()
        print("Please specify the correct path using one of:")
        print("  1. --dataroot /path/to/man-truckscenes")
        print("  2. export TRUCKSCENES_DATAROOT=/path/to/man-truckscenes")
        sys.exit(1)
    
    # Load dataset
    print(f"Loading TruckScenes {args.version} from {args.dataroot}...")
    ts = TruckScenes(version=args.version, dataroot=args.dataroot, verbose=True)
    
    # Run selected mode
    if args.foxglove:
        run_foxglove(ts, args)
    else:
        run_visualization(ts, args)


if __name__ == "__main__":
    main()