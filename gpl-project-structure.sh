#!/bin/bash

# Create GPL (Generative Perception Layers) project structure

echo "🚀 Creating GPL Project Structure..."

# Create main directories
mkdir -p gpl/{core,telemetry,web,config,tests,docs,scripts,data}

# Create subdirectories
mkdir -p gpl/core/{processors,algorithms,utils}
mkdir -p gpl/telemetry/{sensors,collectors,analyzers}
mkdir -p gpl/web/{static,templates,api}
mkdir -p gpl/data/{samples,telemetry_logs,output}

# Create __init__.py files for Python packages
touch gpl/__init__.py
touch gpl/core/__init__.py
touch gpl/core/processors/__init__.py
touch gpl/core/algorithms/__init__.py
touch gpl/core/utils/__init__.py
touch gpl/telemetry/__init__.py
touch gpl/telemetry/sensors/__init__.py
touch gpl/telemetry/collectors/__init__.py
touch gpl/telemetry/analyzers/__init__.py
touch gpl/web/__init__.py
touch gpl/web/api/__init__.py

# Create placeholder files
touch gpl/README.md
touch gpl/requirements.txt
touch gpl/.env.example
touch gpl/.gitignore
touch gpl/Dockerfile
touch gpl/docker-compose.yml

echo "✅ Project structure created!"
echo ""
echo "GPL Project Layout:"
echo "gpl/"
echo "├── core/              # Core HDR processing engine"
echo "│   ├── processors/    # Video/frame processors"
echo "│   ├── algorithms/    # HDR algorithms"
echo "│   └── utils/         # Helper utilities"
echo "├── telemetry/         # Telemetry system"
echo "│   ├── sensors/       # Sensor interfaces"
echo "│   ├── collectors/    # Data collectors"
echo "│   └── analyzers/     # Telemetry analysis"
echo "├── web/               # Web interface"
echo "│   ├── static/        # CSS/JS assets"
echo "│   ├── templates/     # HTML templates"
echo "│   └── api/           # REST/WebSocket APIs"
echo "├── config/            # Configuration files"
echo "├── tests/             # Test suite"
echo "├── docs/              # Documentation"
echo "├── scripts/           # Utility scripts"
echo "└── data/              # Data storage"
echo "    ├── samples/       # Sample videos"
echo "    ├── telemetry_logs/"
echo "    └── output/        # Processed output"