<div align="center">

<h1>MAN TruckScenes devkit</h1>

World's First Public Dataset For Autonomous Trucking

[![Python](https://img.shields.io/badge/python-3-blue.svg)](https://www.python.org/downloads/)
[![Linux](https://img.shields.io/badge/os-linux-blue.svg)](https://www.linux.org/)
[![Windows](https://img.shields.io/badge/os-windows-blue.svg)](https://www.microsoft.com/windows/)
[![arXiv](https://img.shields.io/badge/arXiv-Paper-blue.svg)](https://arxiv.org/abs/2407.07462)

[![Watch the video](https://raw.githubusercontent.com/ffent/truckscenes-media/main/thumbnail.jpg)](https://cdn-assets-eu.frontify.com/s3/frontify-enterprise-files-eu/eyJwYXRoIjoibWFuXC9maWxlXC9lb2s3TGF5V1RXMXYxZU1TUk02US5tcDQifQ:man:MuLfMZFfol1xfBIL7rNw0W4SqczZqwTuzhvI-yxJmdY?width={width}&format=mp4)

</div>

## Overview
- [Website](#website)
- [Installation](#installation)
- [Setup](#setup)
- [Usage](#usage)
- [Foxglove Streaming](#foxglove-streaming)
- [Citation](#citation)

<div id="website"></div>  

## 🌐 Website
To read more about the dataset or download it, please visit [https://www.man.eu/truckscenes](https://www.man.eu/truckscenes)

<div id="installation"></div>  

## 💾 Installation
Our devkit is available and can be installed via pip:
```
pip install truckscenes-devkit
```

If you also want to install all the (optional) dependencies for running the visualizations:
```
pip install "truckscenes-devkit[all]"
```

For more details on the installation see [installation](./docs/installation.md)

<div id="setup"></div> 

## 🔨 Setup
Download **all** archives from our [download page](https://www.man.eu/truckscenes/) or the [AWS Open Data Registry](https://registry.opendata.aws/).  

Unpack the archives to the `/data/man-truckscenes` folder **without** overwriting folders that occur in multiple archives.  
Eventually you should have the following folder structure:
```
/data/man-truckscenes
    samples	-	Sensor data for keyframes.
    sweeps	-	Sensor data for intermediate frames.
    v1.0-*	-	JSON tables that include all the meta data and annotations. Each split (trainval, test, mini) is provided in a separate folder.
```

<div id="usage"></div> 

## 🚀 Usage
Please follow these steps to make yourself familiar with the MAN TruckScenes dataset:
- Read the [dataset description](https://www.man.eu/truckscenes/).
- Explore the dataset [videos](https://cdn-assets-eu.frontify.com/s3/frontify-enterprise-files-eu/eyJwYXRoIjoibWFuXC9maWxlXC9lb2s3TGF5V1RXMXYxZU1TUk02US5tcDQifQ:man:MuLfMZFfol1xfBIL7rNw0W4SqczZqwTuzhvI-yxJmdY?width={width}&format=mp4).
- [Download](https://www.man.eu/truckscenes/) the dataset from our website.
- Make yourself familiar with the [dataset schema](./docs/schema_truckscenes.md)
- Run the [tutorial](./tutorials/truckscenes_tutorial.ipynb) to get started:
- Read the [MAN TruckScenes paper](https://arxiv.org/abs/2407.07462) for a detailed analysis of the dataset.

<div id="foxglove-streaming"></div> 

## 🔌 Foxglove Streaming

This fork adds **real-time streaming to [Foxglove Studio](https://foxglove.dev/)** via WebSocket for interactive 3D visualization.

### Features
- ✅ **Camera streams** - All 6 cameras with full resolution JPEG
- ✅ **Lidar point clouds** - Individual topics per sensor (green spheres)
- ✅ **Radar point clouds** - Individual topics per sensor (orange spheres)
- ✅ **3D bounding boxes** - Object annotations with category-colored boxes
- ✅ **Text labels** - Object class labels above bounding boxes
- ✅ **TF transforms** - Frame positioning for 3D view
- ✅ **Camera calibration** - CameraInfo topics for proper image display

### Installation
```bash
pip install foxglove-websocket  # Required only for Foxglove streaming
```

### Usage
```bash
# Normal visualization (original devkit behavior)
python -m truckscenes

# Render specific scene
python -m truckscenes --scene 2

# Stream to Foxglove Studio
python -m truckscenes --foxglove

# Custom port and data path
python -m truckscenes --foxglove --port 9090 --dataroot /path/to/data
```

### Foxglove Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/camera/CAMERA_*` | CompressedImage | Camera images (6 cameras) |
| `/camera/CAMERA_*/camera_info` | CameraCalibration | Camera intrinsics |
| `/lidar/LIDAR_*` | SceneUpdate | Lidar point clouds (5 sensors) |
| `/radar/RADAR_*` | SceneUpdate | Radar point clouds (6 sensors) |
| `/annotations` | SceneUpdate | 3D bounding boxes with labels |
| `/tf` | FrameTransforms | Coordinate frame transforms |

### Quick Start
1. Start the server: `python -m truckscenes --foxglove`
2. Open [Foxglove Studio](https://studio.foxglove.dev/)
3. Connect to `ws://localhost:8765`
4. Add panels:
   - **Image panel** → select a camera topic
   - **3D panel** → enable `/annotations`, lidar, and radar topics

---

<div id="citation"></div> 

## 📄 Citation
```
@inproceedings{truckscenes2024,
 title = {MAN TruckScenes: A multimodal dataset for autonomous trucking in diverse conditions},
 author = {Fent, Felix and Kuttenreich, Fabian and Ruch, Florian and Rizwin, Farija and Juergens, Stefan and Lechermann, Lorenz and Nissler, Christian and Perl, Andrea and Voll, Ulrich and Yan, Min and Lienkamp, Markus},
 booktitle = {Advances in Neural Information Processing Systems},
 editor = {A. Globerson and L. Mackey and D. Belgrave and A. Fan and U. Paquet and J. Tomczak and C. Zhang},
 pages = {62062--62082},
 publisher = {Curran Associates, Inc.},
 url = {https://proceedings.neurips.cc/paper_files/paper/2024/file/71ac06f0f8450e7d49063c7bfb3257c2-Paper-Datasets_and_Benchmarks_Track.pdf},
 volume = {37},
 year = {2024}
}
```

_Copied and adapted from [nuscenes-devkit](https://github.com/nutonomy/nuscenes-devkit)_
