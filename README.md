📌 Description

This project implements a real-time overlay based on YOLOv8 to detect enemies in CS2. It uses ONNX Runtime for model inference and Pygame for overlay rendering. The integrated aim enables smooth target tracking in real-time (but not realy good).
The model used in this project was entirely created and annotated by me, using the dataset available at this link :  https://universe.roboflow.com/leksa-ub9gf/cs2-dataset-b4kpu/dataset/6

🚀 Features

Real-time enemy player detection

Invisible window overlay (transparent) using Pygame

CUDA (GPU) acceleration for fast inference

Optional aimbot with smooth tracking

Simple user interface with buttons and hotkeys

📂 Project Structure

⚙️ Installation

1️⃣ Requirements

Python 3.8+

CUDA & CuDNN (if using GPU acceleration)

ONNX Runtime with CUDA support

CS:GO in borderless windowed mode

2️⃣ Install Dependencies

Clone the project and install dependencies:

3️⃣ Add the Model

Place the best.onnx file in the main project folder (or train a new model).

🎯 Usage

Run the main script with:

🔑 Hotkeys

F1: Toggle detection on/off

F2: Show/hide labels

K: Enable/disable aimbot (hold to track target)

❌ Files to Exclude (Add to .gitignore)

🛠️ Future Development

Performance optimization improvements

Enhanced aim target selection

📜 License

Open-source project under the MIT license.
