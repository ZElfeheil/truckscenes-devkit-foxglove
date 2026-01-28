#!/usr/bin/env python3
"""
Foxglove WebSocket Streamer for TruckScenes

Streams sensor data from TruckScenes dataset to Foxglove Studio
via the Foxglove WebSocket protocol.

Requires: pip install foxglove-websocket
"""

import asyncio
import json
import base64
import sys
import os
from typing import Dict

import numpy as np
from pyquaternion import Quaternion

try:
    from foxglove_websocket.server import FoxgloveServer
    from foxglove_websocket.types import ChannelId
except ImportError:
    print("Error: foxglove-websocket not installed.")
    print("Install with: pip install foxglove-websocket")
    sys.exit(1)

from truckscenes import TruckScenes
from truckscenes.utils.data_classes import LidarPointCloud, RadarPointCloud


# Category colors (RGBA)
CATEGORY_COLORS = {
    "vehicle.car": {"r": 0.0, "g": 0.5, "b": 1.0, "a": 0.7},
    "vehicle.truck": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 0.7},
    "vehicle.bus": {"r": 1.0, "g": 0.5, "b": 0.0, "a": 0.7},
    "vehicle.bicycle": {"r": 0.0, "g": 1.0, "b": 0.0, "a": 0.7},
    "vehicle.motorcycle": {"r": 0.5, "g": 0.0, "b": 1.0, "a": 0.7},
    "vehicle.trailer": {"r": 0.8, "g": 0.4, "b": 0.0, "a": 0.7},
    "human.pedestrian.adult": {"r": 1.0, "g": 1.0, "b": 0.0, "a": 0.7},
    "human.pedestrian.child": {"r": 1.0, "g": 0.8, "b": 0.0, "a": 0.7},
    "movable_object": {"r": 0.5, "g": 0.5, "b": 0.5, "a": 0.7},
}


class FoxgloveStreamer:
    """Streams TruckScenes data to Foxglove Studio via WebSocket."""
    
    def __init__(self, ts: TruckScenes, port: int = 8765):
        self.ts = ts
        self.port = port
        self.running = False
        self.channels: Dict[str, ChannelId] = {}
        self.tf_channel = None
        self.annotations_channel = None
    
    def run(self):
        """Start the Foxglove streaming server."""
        asyncio.run(self._run_server())
    
    async def _run_server(self):
        """Main async server loop."""
        async with FoxgloveServer(
            host="0.0.0.0",
            port=self.port,
            name="TruckScenes Streamer"
        ) as server:
            print(f"Foxglove server started on ws://localhost:{self.port}")
            print("Connect Foxglove Studio to this address.")
            
            await self._register_channels(server)
            
            self.running = True
            await self._stream_data(server)
    
    async def _register_channels(self, server: FoxgloveServer):
        """Register individual channels for each sensor."""
        
        for sensor in self.ts.sensor:
            channel = sensor['channel']
            if 'CAMERA' in channel:
                # Schema that tells Foxglove the data field is base64 encoded
                camera_schema = json.dumps({
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "object"},
                        "frame_id": {"type": "string"},
                        "format": {"type": "string"},
                        "data": {"type": "string", "contentEncoding": "base64"}
                    }
                })
                self.channels[channel] = await server.add_channel({
                    "topic": f"/camera/{channel}",
                    "encoding": "json",
                    "schemaName": "foxglove.CompressedImage",
                    "schemaEncoding": "jsonschema",
                    "schema": camera_schema
                })
                # CameraInfo channel to remove Foxglove warning
                self.channels[f"{channel}_info"] = await server.add_channel({
                    "topic": f"/camera/{channel}/camera_info",
                    "encoding": "json",
                    "schemaName": "foxglove.CameraCalibration",
                    "schema": ""
                })
            elif 'LIDAR' in channel:
                self.channels[channel] = await server.add_channel({
                    "topic": f"/lidar/{channel}",
                    "encoding": "json",
                    "schemaName": "foxglove.SceneUpdate",
                    "schema": ""
                })
            elif 'RADAR' in channel:
                self.channels[channel] = await server.add_channel({
                    "topic": f"/radar/{channel}",
                    "encoding": "json",
                    "schemaName": "foxglove.SceneUpdate",
                    "schema": ""
                })
        
        # TF channel
        self.tf_channel = await server.add_channel({
            "topic": "/tf",
            "encoding": "json",
            "schemaName": "foxglove.FrameTransforms",
            "schema": ""
        })
        
        # Annotations channel (3D bounding boxes)
        self.annotations_channel = await server.add_channel({
            "topic": "/annotations",
            "encoding": "json",
            "schemaName": "foxglove.SceneUpdate",
            "schema": ""
        })
        
        lidar_count = sum(1 for ch in self.channels if 'LIDAR' in ch)
        radar_count = sum(1 for ch in self.channels if 'RADAR' in ch)
        camera_count = sum(1 for ch in self.channels if 'CAMERA' in ch)
        print(f"Registered {camera_count} cameras, {lidar_count} lidars, {radar_count} radars + /annotations + /tf")
    
    async def _stream_data(self, server: FoxgloveServer):
        """Stream sensor data frame by frame."""
        
        for scene_idx, scene in enumerate(self.ts.scene):
            print(f"Streaming scene {scene_idx + 1}/{len(self.ts.scene)}")
            
            current_token = scene['first_sample_token']
            frame_count = 0
            
            while current_token and self.running:
                sample = self.ts.get('sample', current_token)
                timestamp = sample['timestamp']
                
                # Send TF
                await self._send_transforms(server, timestamp)
                
                # Send each sensor data to its own topic
                for channel, sd_token in sample['data'].items():
                    if channel in self.channels:
                        if 'CAMERA' in channel:
                            await self._send_camera(server, channel, sd_token, timestamp)
                        elif 'LIDAR' in channel:
                            await self._send_pointcloud(server, channel, sd_token, timestamp, is_lidar=True)
                        elif 'RADAR' in channel:
                            await self._send_pointcloud(server, channel, sd_token, timestamp, is_lidar=False)
                
                # Send annotations
                await self._send_annotations(server, sample, timestamp)
                
                frame_count += 1
                if frame_count % 10 == 0:
                    print(f"  Frame {frame_count}")
                
                await asyncio.sleep(0.1)
                current_token = sample['next']
            
            if not self.running:
                break
        
        print("Streaming complete.")
    
    async def _send_transforms(self, server: FoxgloveServer, timestamp: int):
        """Send TF transforms."""
        ts = self._ts(timestamp)
        transforms = [{
            "timestamp": ts,
            "parent_frame_id": "world",
            "child_frame_id": "base_link",
            "translation": {"x": 0, "y": 0, "z": 0},
            "rotation": {"x": 0, "y": 0, "z": 0, "w": 1}
        }]
        msg = json.dumps({"transforms": transforms}).encode()
        await server.send_message(self.tf_channel, timestamp * 1000, msg)
    
    async def _send_camera(self, server: FoxgloveServer, channel: str, sd_token: str, timestamp: int):
        """Send camera image as CompressedImage with CameraCalibration."""
        try:
            path = self.ts.get_sample_data_path(sd_token)
            with open(path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('ascii')
            
            # Send image
            msg = json.dumps({
                "timestamp": self._ts(timestamp),
                "frame_id": "base_link",
                "format": "jpeg",
                "data": data
            }).encode()
            await server.send_message(self.channels[channel], timestamp * 1000, msg)
            
            # Send CameraCalibration (camera_info) - basic calibration
            info_key = f"{channel}_info"
            if info_key in self.channels:
                # Default camera intrinsics (1920x1080)
                fx, fy = 1000.0, 1000.0  # Focal length
                cx, cy = 960.0, 540.0   # Principal point
                camera_info = json.dumps({
                    "timestamp": self._ts(timestamp),
                    "frame_id": "base_link",
                    "width": 1920,
                    "height": 1080,
                    "distortion_model": "plumb_bob",
                    "D": [0.0, 0.0, 0.0, 0.0, 0.0],
                    "K": [fx, 0, cx, 0, fy, cy, 0, 0, 1],
                    "R": [1, 0, 0, 0, 1, 0, 0, 0, 1],
                    "P": [fx, 0, cx, 0, 0, fy, cy, 0, 0, 0, 1, 0]
                }).encode()
                await server.send_message(self.channels[info_key], timestamp * 1000, camera_info)
        except Exception as e:
            print(f"Camera error {channel}: {e}")
    
    async def _send_pointcloud(self, server: FoxgloveServer, channel: str, sd_token: str, 
                                timestamp: int, is_lidar: bool):
        """Send a single lidar or radar as SceneUpdate to its own topic."""
        try:
            path = self.ts.get_sample_data_path(sd_token)
            
            if is_lidar:
                pc = LidarPointCloud.from_file(path)
                size = 0.1
                max_pts = 3000
                
                # Single green color for all lidar points
                n_pts = min(pc.points.shape[1], max_pts)
                spheres = []
                for i in range(n_pts):
                    spheres.append({
                        "pose": {"position": {"x": float(pc.points[0, i]), 
                                             "y": float(pc.points[1, i]), 
                                             "z": float(pc.points[2, i])}, 
                                "orientation": {"x":0,"y":0,"z":0,"w":1}}, 
                        "size": {"x": size, "y": size, "z": size}, 
                        "color": {"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0}
                    })
            else:
                pc = RadarPointCloud.from_file(path)
                size = 0.3
                max_pts = 800
                
                # RCS-based coloring for radar (row 6 is RCS in dBsm)
                # RCS range: typically -20 to +34 dBsm
                n_pts = min(pc.points.shape[1], max_pts)
                spheres = []
                for i in range(n_pts):
                    rcs = float(pc.points[6, i])  # RCS in dBsm
                    # Normalize RCS to 0-1 range (clamp to -20 to +30 dBsm)
                    rcs_norm = max(0.0, min(1.0, (rcs + 20) / 50))
                    
                    # Color gradient: blue (low RCS) -> yellow -> red (high RCS)
                    if rcs_norm < 0.5:
                        r = rcs_norm * 2
                        g = rcs_norm * 2
                        b = 1.0 - rcs_norm * 2
                    else:
                        r = 1.0
                        g = 1.0 - (rcs_norm - 0.5) * 2
                        b = 0.0
                    
                    spheres.append({
                        "pose": {"position": {"x": float(pc.points[0, i]), 
                                             "y": float(pc.points[1, i]), 
                                             "z": float(pc.points[2, i])}, 
                                "orientation": {"x":0,"y":0,"z":0,"w":1}}, 
                        "size": {"x": size, "y": size, "z": size}, 
                        "color": {"r": r, "g": g, "b": b, "a": 1.0}
                    })
            
            if spheres:
                entity = {
                    "timestamp": self._ts(timestamp),
                    "frame_id": "base_link",
                    "id": channel,
                    "lifetime": {"sec": 0, "nsec": 500000000},
                    "frame_locked": True,
                    "metadata": [],
                    "arrows": [],
                    "cubes": [],
                    "spheres": spheres,
                    "cylinders": [],
                    "lines": [],
                    "triangles": [],
                    "texts": [],
                    "models": []
                }
                msg = json.dumps({"entities": [entity], "deletions": []}).encode()
                await server.send_message(self.channels[channel], timestamp * 1000, msg)
        except Exception as e:
            print(f"Pointcloud error {channel}: {e}")
    
    async def _send_annotations(self, server: FoxgloveServer, sample: dict, timestamp: int):
        """Send 3D bounding box annotations."""
        try:
            # Get ego pose from a lidar sample_data
            lidar_token = sample['data'].get('LIDAR_LEFT') or sample['data'].get('LIDAR_TOP_FRONT')
            if not lidar_token:
                return
            
            sd = self.ts.get('sample_data', lidar_token)
            ego_pose = self.ts.get('ego_pose', sd['ego_pose_token'])
            ego_translation = np.array(ego_pose['translation'])
            ego_rotation = Quaternion(ego_pose['rotation'])
            
            cubes = []
            texts = []
            
            for ann_token in sample['anns']:
                ann = self.ts.get('sample_annotation', ann_token)
                inst = self.ts.get('instance', ann['instance_token'])
                cat = self.ts.get('category', inst['category_token'])
                category_name = cat['name']
                
                # Transform annotation to ego frame
                ann_translation = np.array(ann['translation'])
                relative_pos = ann_translation - ego_translation
                relative_pos = ego_rotation.inverse.rotate(relative_pos)
                
                # Combine rotations
                ann_rotation = Quaternion(ann['rotation'])
                relative_rot = ego_rotation.inverse * ann_rotation
                
                # Get size (width, length, height)
                size = ann['size']  # [width, length, height]
                
                # Get color based on category
                color = CATEGORY_COLORS.get(category_name, {"r": 0.5, "g": 0.5, "b": 0.5, "a": 0.7})
                
                cubes.append({
                    "pose": {
                        "position": {"x": float(relative_pos[0]), "y": float(relative_pos[1]), "z": float(relative_pos[2])},
                        "orientation": {"x": float(relative_rot.x), "y": float(relative_rot.y), 
                                       "z": float(relative_rot.z), "w": float(relative_rot.w)}
                    },
                    "size": {"x": float(size[1]), "y": float(size[0]), "z": float(size[2])},  # l, w, h
                    "color": color
                })
                
                # Add label text above box
                texts.append({
                    "pose": {
                        "position": {"x": float(relative_pos[0]), "y": float(relative_pos[1]), "z": float(relative_pos[2] + size[2]/2 + 0.5)},
                        "orientation": {"x": 0, "y": 0, "z": 0, "w": 1}
                    },
                    "billboard": True,
                    "font_size": 12.0,
                    "scale_invariant": True,
                    "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
                    "text": category_name.split('.')[-1]  # Just the last part (e.g., "car" from "vehicle.car")
                })
            
            if cubes:
                entity = {
                    "timestamp": self._ts(timestamp),
                    "frame_id": "base_link",
                    "id": "annotations",
                    "lifetime": {"sec": 0, "nsec": 500000000},
                    "frame_locked": True,
                    "metadata": [],
                    "arrows": [],
                    "cubes": cubes,
                    "spheres": [],
                    "cylinders": [],
                    "lines": [],
                    "triangles": [],
                    "texts": texts,
                    "models": []
                }
                msg = json.dumps({"entities": [entity], "deletions": []}).encode()
                await server.send_message(self.annotations_channel, timestamp * 1000, msg)
        except Exception as e:
            print(f"Annotations error: {e}")
    
    def _ts(self, timestamp_us: int) -> dict:
        """Convert microsecond timestamp to Foxglove format."""
        return {"sec": timestamp_us // 1000000, "nsec": (timestamp_us % 1000000) * 1000}


def main():
    """Entry point for Foxglove streaming."""
    import argparse
    parser = argparse.ArgumentParser(description="Stream TruckScenes to Foxglove")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--dataroot", type=str, 
                        default=os.getenv("TRUCKSCENES_DATAROOT", "../data/man-truckscenes"))
    parser.add_argument("--version", type=str,
                        default=os.getenv("TRUCKSCENES_VERSION", "v1.1-mini"))
    args = parser.parse_args()
    
    print(f"Loading TruckScenes {args.version} from {args.dataroot}...")
    ts = TruckScenes(version=args.version, dataroot=args.dataroot, verbose=True)
    
    print(f"Starting Foxglove server on port {args.port}...")
    FoxgloveStreamer(ts, port=args.port).run()


if __name__ == "__main__":
    main()
